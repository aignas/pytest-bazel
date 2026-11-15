import pytest

from pytest_bazel.main import BazelEnv
from pytest_bazel.main import main as _main

pytest_plugins = ["pytester"]


def _env(failure_file):
    return BazelEnv(
        {"BAZEL_TEST": "1", "TEST_INFRASTRUCTURE_FAILURE_FILE": str(failure_file)}
    )


@pytest.mark.parametrize(
    "exit_code",
    [pytest.ExitCode.INTERNAL_ERROR, pytest.ExitCode.USAGE_ERROR],
    ids=lambda c: c.name,
)
def test_written_when_pytest_fails(tmp_path, exit_code):
    failure_file = tmp_path / "infrastructure_failure"

    got = _main(args=["-q"], pytest_main=lambda _: exit_code, env=_env(failure_file))

    assert got == exit_code
    assert exit_code.name in failure_file.read_text()


@pytest.mark.parametrize(
    "exit_code",
    [
        pytest.ExitCode.OK,
        pytest.ExitCode.TESTS_FAILED,
        pytest.ExitCode.INTERRUPTED,
        pytest.ExitCode.NO_TESTS_COLLECTED,
    ],
    ids=lambda c: c.name,
)
def test_not_written_when_tests_run(tmp_path, exit_code):
    failure_file = tmp_path / "infrastructure_failure"

    _main(args=["-q"], pytest_main=lambda _: exit_code, env=_env(failure_file))

    assert not failure_file.exists()


def test_unknown_flag(pytester, tmp_path):
    pytester.makepyfile("def test_ok(): pass")
    failure_file = tmp_path / "infrastructure_failure"

    got = _main(
        args=["--no-such-flag"],
        pytest_main=lambda args: pytester.runpytest(*args).ret,
        env=_env(failure_file),
    )

    assert got == pytest.ExitCode.USAGE_ERROR
    assert "unknown flag" in failure_file.read_text()


if __name__ == "__main__":
    from pytest_bazel import main

    main()
