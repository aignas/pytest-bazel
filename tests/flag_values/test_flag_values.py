"""An invalid value of an opt-in flag is a usage error, not a traceback."""

import pytest

from pytest_bazel._impl.main import BazelEnv
from pytest_bazel._impl.main import main as _main


def _never(args):
    pytest.fail(f"pytest ran with {args}")


def test_invalid_value_is_a_usage_error(tmp_path, capsys):
    failure_file = tmp_path / "infrastructure_failure"
    env = BazelEnv(
        {
            "BAZEL_TEST": "1",
            "PYTEST_BAZEL_JUNIT_OUTPUT": "true",
            "PYTEST_BAZEL_EXACT_TEST_FILTER": "yes",
            "TEST_INFRASTRUCTURE_FAILURE_FILE": str(failure_file),
        }
    )

    code = _main(args=[], pytest_main=_never, env=env)

    assert code == pytest.ExitCode.USAGE_ERROR
    want = [
        "pytest_bazel: PYTEST_BAZEL_EXACT_TEST_FILTER must be 0 or 1, got 'yes'",
        "pytest_bazel: PYTEST_BAZEL_JUNIT_OUTPUT must be 0 or 1, got 'true'",
    ]
    assert sorted(capsys.readouterr().err.splitlines()) == want
    assert sorted(failure_file.read_text().splitlines()) == want


@pytest.mark.parametrize("value", ["0", "1"])
def test_valid_values_run_pytest(value):
    ran = []
    env = BazelEnv({"PYTEST_BAZEL_JUNIT_OUTPUT": value})

    code = _main(args=[], pytest_main=lambda args: ran.append(args) or 0, env=env)

    assert code == 0
    assert ran


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
