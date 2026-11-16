"""`_pytest_args` only computes args, `_prepare` sets up the process."""

from pytest_bazel._impl.main import BazelEnv, _prepare, _pytest_args


def _sharded(tmp_path):
    return {
        "BAZEL_TEST": "1",
        "TEST_SHARD_INDEX": "0",
        "TEST_TOTAL_SHARDS": "2",
        "TEST_SHARD_STATUS_FILE": str(tmp_path / "status"),
    }


def test_pytest_args_has_no_side_effects(tmp_path):
    _pytest_args(args=[], env=BazelEnv(_sharded(tmp_path)))

    assert not (tmp_path / "status").exists()


def test_prepare_advertises_sharding(tmp_path):
    _prepare(BazelEnv(_sharded(tmp_path)))

    assert (tmp_path / "status").exists()


def test_prepare_without_sharding(tmp_path):
    env = _sharded(tmp_path)
    del env["TEST_TOTAL_SHARDS"]

    _prepare(BazelEnv(env))

    assert not (tmp_path / "status").exists()


def test_prepare_does_nothing_without_bazel_test(tmp_path):
    env = _sharded(tmp_path)
    del env["BAZEL_TEST"]

    _prepare(BazelEnv(env))

    assert not (tmp_path / "status").exists()


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
