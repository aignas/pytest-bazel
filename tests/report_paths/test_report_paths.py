"""The locations in the pytest report must be easy to open in an editor.

That is, relative to the runfiles root, which is the same as the
workspace root for the main repository, and never absolute paths into the
bazel sandbox.
"""

import os
import re
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

from pytest_bazel.main import _relative_warning_paths

_SAMPLE = "tests/report_paths/sample/failing.py"

# `path/to/file.py:12` as pytest and Python print code locations.
_LOCATION = re.compile(r"(?P<path>[^\s\"'():]+\.py):(?P<line>\d+)")


def _format(filename):
    return warnings.formatwarning("msg", UserWarning, filename, 7)


def test_warning_paths_relative_to_runfiles_root(tmp_path):
    start = tmp_path / "runfiles" / "_main"

    with _relative_warning_paths(start):
        in_main = _format(str(start / "pkg" / "mod.py"))
        in_other_repo = _format(str(tmp_path / "runfiles" / "other+" / "mod.py"))
        outside = _format("/usr/lib/python3/mod.py")
        relative = _format("pkg/mod.py")

    assert in_main.startswith(str(Path("pkg", "mod.py")) + ":7:")
    assert in_other_repo.startswith(str(Path("..", "other+", "mod.py")) + ":7:")
    assert outside.startswith("/usr/lib/python3/mod.py:7:")
    assert relative.startswith("pkg/mod.py:7:")


def test_formatwarning_is_restored(tmp_path):
    original = warnings.formatwarning

    with _relative_warning_paths(tmp_path):
        assert warnings.formatwarning is not original

    assert warnings.formatwarning is original


@pytest.mark.skipif("BAZEL_TEST" not in os.environ, reason="needs bazel test")
def test_report_locations_can_be_opened():
    """Run the failing sample through pytest_bazel and check its report."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("TEST_", "XML_", "TESTBRIDGE_"))
    }
    env["PYTHONPATH"] = os.pathsep.join(sys.path)

    result = subprocess.run(
        [sys.executable, "-m", "pytest_bazel", "-p", "no:randomly", _SAMPLE],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == pytest.ExitCode.TESTS_FAILED, output

    locations = {(m["path"], int(m["line"])) for m in _LOCATION.finditer(output)}
    for want in [
        (_SAMPLE, 12),  # the assert in test_assert
        (_SAMPLE, 21),  # the broken fixture
        ("tests/report_paths/helper/helper.py", 5),  # the assert in the helper
        ("tests/report_paths/helper/helper.py", 9),  # the warning
    ]:
        assert want in locations, output

    for path, line in sorted(locations):
        assert not Path(path).is_absolute(), f"{path}:{line} in\n{output}"
        assert Path(path).is_file(), f"{path}:{line} does not exist in\n{output}"


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
