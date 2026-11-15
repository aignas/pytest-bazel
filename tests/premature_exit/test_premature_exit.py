import os
import subprocess
import sys
from pathlib import Path

import pytest

from pytest_bazel.main import BazelEnv
from pytest_bazel.main import main as _main


def _env(premature_exit_file):
    return BazelEnv(
        {"BAZEL_TEST": "1", "TEST_PREMATURE_EXIT_FILE": str(premature_exit_file)}
    )


def test_file_exists_while_pytest_runs(tmp_path):
    premature_exit_file = tmp_path / "premature_exit"
    seen = []

    def pytest_main(_args):
        seen.append(premature_exit_file.exists())
        return 0

    _main(args=["-q"], pytest_main=pytest_main, env=_env(premature_exit_file))

    assert seen == [True]
    assert not premature_exit_file.exists()


@pytest.mark.parametrize("exit_code", [0, 1])
def test_file_is_removed_when_pytest_returns(tmp_path, exit_code):
    premature_exit_file = tmp_path / "premature_exit"

    _main(
        args=["-q"],
        pytest_main=lambda _args: exit_code,
        env=_env(premature_exit_file),
    )

    assert not premature_exit_file.exists()


def test_file_is_kept_when_pytest_does_not_return(tmp_path):
    premature_exit_file = tmp_path / "premature_exit"

    def pytest_main(_args):
        raise SystemExit(0)

    with pytest.raises(SystemExit):
        _main(args=["-q"], pytest_main=pytest_main, env=_env(premature_exit_file))

    assert premature_exit_file.exists()


def test_os_exit_in_a_test_leaves_the_file(tmp_path):
    test_file = tmp_path / "test_exit.py"
    test_file.write_text("import os\n\ndef test_exit():\n    os._exit(0)\n")
    premature_exit_file = tmp_path / "premature_exit"
    env = {
        **os.environ,
        "BAZEL_TEST": "1",
        "PYTHONPATH": os.pathsep.join(sys.path),
        "TEST_PREMATURE_EXIT_FILE": str(premature_exit_file),
    }
    # Do not pass on the bazel env of this test, e.g. TEST_TMPDIR, which is
    # a parent of the cwd of the subprocess.
    for var in (
        "TEST_SHARD_INDEX",
        "TEST_TARGET",
        "TEST_TMPDIR",
        "TEST_TOTAL_SHARDS",
        "XML_OUTPUT_FILE",
    ):
        env.pop(var, None)

    result = subprocess.run(
        [sys.executable, "-m", "pytest_bazel", str(test_file)],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert premature_exit_file.exists(), "so the file must tell bazel it failed"


@pytest.mark.skipif("BAZEL_TEST" not in os.environ, reason="needs bazel test")
def test_bazel_sets_the_file():
    """This target only passes if pytest_bazel removes the file again."""
    assert Path(os.environ["TEST_PREMATURE_EXIT_FILE"]).exists()


if __name__ == "__main__":
    from pytest_bazel import main

    main()
