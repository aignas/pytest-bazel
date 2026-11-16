"""`_pytest_args` only computes args, `_prepare` sets up the process."""

import importlib.util
import random

import pytest

from pytest_bazel.main import BazelEnv, _prepare, _pytest_args


def _sharded(tmp_path):
    return {
        "BAZEL_TEST": "1",
        "TEST_SHARD_INDEX": "0",
        "TEST_TOTAL_SHARDS": "2",
        "TEST_SHARD_STATUS_FILE": str(tmp_path / "status"),
        "TEST_RANDOM_SEED": "7",
    }


@pytest.fixture
def without_pytest_randomly(monkeypatch):
    find_spec = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name, *a: None if name == "pytest_randomly" else find_spec(name, *a),
    )


@pytest.mark.usefixtures("without_pytest_randomly")
def test_pytest_args_has_no_side_effects(tmp_path):
    random.seed(1)
    want = random.random()
    random.seed(1)

    _pytest_args(args=[], env=BazelEnv(_sharded(tmp_path)))

    assert not (tmp_path / "status").exists()
    assert random.random() == want


def test_prepare_advertises_sharding(tmp_path):
    _prepare(BazelEnv(_sharded(tmp_path)))

    assert (tmp_path / "status").exists()


def test_prepare_without_sharding(tmp_path):
    env = _sharded(tmp_path)
    del env["TEST_TOTAL_SHARDS"]

    _prepare(BazelEnv(env))

    assert not (tmp_path / "status").exists()


@pytest.mark.usefixtures("without_pytest_randomly")
def test_prepare_does_nothing_without_bazel_test(tmp_path):
    env = _sharded(tmp_path)
    del env["BAZEL_TEST"]
    random.seed(1)
    want = random.random()
    random.seed(1)

    _prepare(BazelEnv(env))

    assert not (tmp_path / "status").exists()
    assert random.random() == want


@pytest.mark.usefixtures("without_pytest_randomly")
def test_prepare_seeds_random(tmp_path):
    _prepare(BazelEnv(_sharded(tmp_path)))
    got = random.random()

    random.seed(7)
    assert got == random.random()


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
