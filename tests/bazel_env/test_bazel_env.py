"""BazelEnv behaves like the dataclass it was."""

from pytest_bazel.main import BazelEnv


def test_construct():
    env = {"BAZEL_TEST": "1"}

    assert BazelEnv(env).env is env
    assert BazelEnv(env=env).env is env


def test_equality():
    assert BazelEnv({"A": "1"}) == BazelEnv({"A": "1"})
    assert BazelEnv({"A": "1"}) != BazelEnv({"A": "2"})
    assert BazelEnv({"A": "1"}) != {"A": "1"}


def test_repr():
    assert repr(BazelEnv({"A": "1"})) == "BazelEnv(env={'A': '1'})"


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
