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
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from pytest_bazel._impl.main import BazelEnv
from pytest_bazel._impl.main import main as _main
from pytest_bazel._impl.warning_paths import (
    _relative_to_runfiles,
    _relative_warning_paths,
)

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


@pytest.mark.parametrize(
    ("start", "filename", "want"),
    [
        pytest.param(
            PurePosixPath("/r/_main"), "/r/_main/pkg/mod.py", "pkg/mod.py", id="posix"
        ),
        pytest.param(
            PurePosixPath("/r/_main"),
            "/r/other+/mod.py",
            "../other+/mod.py",
            id="posix_other_repo",
        ),
        pytest.param(
            PurePosixPath("/r/_main"),
            "/usr/lib/mod.py",
            "/usr/lib/mod.py",
            id="posix_outside",
        ),
        pytest.param(
            PureWindowsPath("C:/r/_main"),
            r"C:\r\_main\pkg\mod.py",
            r"pkg\mod.py",
            id="windows",
        ),
        pytest.param(
            PureWindowsPath("C:/r/_main"),
            r"c:\R\_MAIN\pkg\mod.py",
            r"pkg\mod.py",
            id="windows_case",
        ),
        pytest.param(
            PureWindowsPath("C:/r/_main"),
            r"C:\r\other+\mod.py",
            r"..\other+\mod.py",
            id="windows_other_repo",
        ),
        pytest.param(
            PureWindowsPath("C:/r/_main"),
            r"D:\r\_main\mod.py",
            r"D:\r\_main\mod.py",
            id="windows_other_drive",
        ),
        pytest.param(
            PureWindowsPath("C:/r/_main"),
            r"\\server\share\mod.py",
            r"\\server\share\mod.py",
            id="windows_unc",
        ),
        pytest.param(
            PurePosixPath("/r/_main"), "<string>", "<string>", id="not_a_file"
        ),
        pytest.param(
            PurePosixPath("/r/_main"), "pkg/mod.py", "pkg/mod.py", id="relative"
        ),
    ],
)
def test_relative_to_runfiles(start, filename, want):
    assert _relative_to_runfiles(filename, start) == want


def test_formatwarning_is_restored(tmp_path):
    original = warnings.formatwarning

    with _relative_warning_paths(tmp_path):
        assert warnings.formatwarning is not original

    assert warnings.formatwarning is original


@pytest.mark.parametrize(
    ("environ", "want_wrapped"),
    [
        pytest.param({"BAZEL_TEST": "1"}, True, id="bazel_test"),
        # `bazel run` of a test target sets BAZEL_TEST too.
        pytest.param(
            {"BAZEL_TEST": "1", "BUILD_WORKSPACE_DIRECTORY": "/ws"},
            False,
            id="bazel_run",
        ),
        pytest.param({}, False, id="without_bazel"),
    ],
)
def test_only_under_bazel_test(environ, want_wrapped):
    original = warnings.formatwarning
    seen = []

    def pytest_main(_args):
        seen.append(warnings.formatwarning is not original)
        return 0

    _main(args=["-q"], pytest_main=pytest_main, env=BazelEnv(environ))

    assert seen == [want_wrapped]
    assert warnings.formatwarning is original


def _run_sample(*args, bazel_test):
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("TEST_", "XML_", "TESTBRIDGE_", "BAZEL_TEST"))
    }
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    if bazel_test:
        env["BAZEL_TEST"] = "1"

    result = subprocess.run(
        [sys.executable, "-m", "pytest_bazel", "-p", "no:randomly", *args, _SAMPLE],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == pytest.ExitCode.TESTS_FAILED, output
    return output


@pytest.mark.skipif("BAZEL_TEST" not in os.environ, reason="needs bazel test")
def test_absolute_warning_paths_without_bazel_test():
    output = _run_sample(bazel_test=False)

    helper = Path.cwd() / "tests" / "report_paths" / "helper" / "helper.py"
    assert f"{helper}:9: UserWarning" in output, output


def _check_locations(output, want):
    locations = {(m["path"], int(m["line"])) for m in _LOCATION.finditer(output)}
    for location in want:
        assert location in locations, output

    for path, line in sorted(locations):
        assert not Path(path).is_absolute(), f"{path}:{line} in\n{output}"
        assert Path(path).is_file(), f"{path}:{line} does not exist in\n{output}"


@pytest.mark.skipif("BAZEL_TEST" not in os.environ, reason="needs bazel test")
def test_report_locations_can_be_opened():
    """Run the failing sample like bazel test and check its report."""
    output = _run_sample(bazel_test=True)

    _check_locations(
        output,
        [
            (_SAMPLE, 12),  # the assert in test_assert
            (_SAMPLE, 21),  # the broken fixture
            (_SAMPLE, 34),  # the assert after the test changed the directory
            ("tests/report_paths/helper/helper.py", 5),  # the assert in the helper
            ("tests/report_paths/helper/helper.py", 9),  # the warning
        ],
    )


@pytest.mark.skipif("BAZEL_TEST" not in os.environ, reason="needs bazel test")
def test_report_locations_with_tb_line():
    """`--tb=line` prints only where each test failed, not for errors."""
    output = _run_sample("--tb=line", bazel_test=True)

    _check_locations(
        output,
        [
            (_SAMPLE, 12),
            (_SAMPLE, 34),
            ("tests/report_paths/helper/helper.py", 5),
        ],
    )


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
