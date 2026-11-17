"""TEST_RANDOM_SEED and TEST_RUN_NUMBER seed pytest-randomly or `random`."""

import pytest

from pytest_bazel._impl.main import BazelEnv, _pytest_args

pytest_plugins = ["pytester"]

# The first `random.random()` after `random.seed(7)`.
_TEST = """
import random

def test_seeded():
    assert random.random() == random.Random(7).random()
"""


def _args(*args, **env):
    return _pytest_args(args=list(args), env=BazelEnv({"BAZEL_TEST": "1", **env}))


@pytest.mark.parametrize("var", ["TEST_RANDOM_SEED", "TEST_RUN_NUMBER"])
def test_seeds_pytest_randomly(pytester, var):
    pytester.makepyfile("def test_ok(): pass\n")

    result = pytester.runpytest_subprocess(*_args(**{var: "7"}))

    assert result.ret == pytest.ExitCode.OK, result.stdout.str()
    result.stdout.fnmatch_lines(["Using --randomly-seed=7"])


def test_seeds_pytest_randomly_loaded_by_module_name(pytester, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    pytester.makepyfile("def test_ok(): pass\n")

    result = pytester.runpytest_subprocess(
        *_args("-p", "pytest_randomly", TEST_RUN_NUMBER="7")
    )

    assert result.ret == pytest.ExitCode.OK, result.stdout.str()
    result.stdout.fnmatch_lines(["Using --randomly-seed=7"])


def test_user_seed_wins(pytester):
    pytester.makepyfile("def test_ok(): pass\n")

    result = pytester.runpytest_subprocess(
        *_args("--randomly-seed=3", TEST_RANDOM_SEED="7")
    )

    result.stdout.fnmatch_lines(["Using --randomly-seed=3"])


def test_seeds_random_without_pytest_randomly(pytester):
    pytester.makepyfile(_TEST)

    result = pytester.runpytest_subprocess(
        *_args("-p", "no:randomly", "-p", "no:cacheprovider", TEST_RUN_NUMBER="7")
    )

    assert result.ret == pytest.ExitCode.OK, result.stdout.str()


def test_no_seed_by_default():
    assert "pytest_bazel._impl.random_seed" not in _args()


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
