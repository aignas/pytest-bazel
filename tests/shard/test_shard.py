import importlib.util
import random

import pytest

from pytest_bazel._impl.main import BazelEnv, _pytest_args
from pytest_bazel._impl.shard import select_shard

pytest_plugins = ["pytester"]

_NUM_TESTS = 20


def _node_ids(n):
    return [f"test_mod.py::test_{i}" for i in range(n)]


@pytest.mark.parametrize("num_tests", [0, 1, 7, 37])
@pytest.mark.parametrize("total", [1, 2, 3, 5])
def test_every_test_runs_in_exactly_one_shard(num_tests, total):
    node_ids = _node_ids(num_tests)

    shards = [select_shard(node_ids, i, total) for i in range(total)]

    assert sum(len(s) for s in shards) == num_tests
    assert set().union(*shards) == set(node_ids)


@pytest.mark.parametrize("total", [2, 3, 5])
def test_shards_are_balanced(total):
    node_ids = _node_ids(37)

    sizes = [len(select_shard(node_ids, i, total)) for i in range(total)]

    assert max(sizes) - min(sizes) <= 1, sizes


def test_shards_do_not_depend_on_collection_order():
    node_ids = _node_ids(37)
    shuffled = list(node_ids)
    random.Random(42).shuffle(shuffled)

    for i in range(3):
        assert select_shard(shuffled, i, 3) == select_shard(node_ids, i, 3)


@pytest.fixture
def _test_file(pytester):
    pytester.makepyfile("\n".join(f"def test_{i}(): pass" for i in range(_NUM_TESTS)))


def _run_shards(pytester, total, args_for_shard):
    shards = []
    for i in range(total):
        rec = pytester.inline_run(*args_for_shard(i))
        assert rec.ret == pytest.ExitCode.OK
        passed, _, _ = rec.listoutcomes()
        assert len(rec.getcalls("pytest_deselected")) == (1 if total > 1 else 0)
        shards.append({r.nodeid for r in passed})
    return shards


@pytest.mark.usefixtures("_test_file")
def test_plugin_splits_tests_across_shards(pytester):
    shards = _run_shards(
        pytester,
        3,
        lambda i: [
            "-p",
            "pytest_bazel._impl.shard",
            f"--bazel-shard-index={i}",
            "--bazel-total-shards=3",
        ],
    )

    assert sum(len(s) for s in shards) == _NUM_TESTS
    assert len(set().union(*shards)) == _NUM_TESTS


@pytest.mark.usefixtures("_test_file")
def test_plugin_runs_everything_by_default(pytester):
    (shard,) = _run_shards(pytester, 1, lambda _: ["-p", "pytest_bazel._impl.shard"])

    assert len(shard) == _NUM_TESTS


@pytest.mark.usefixtures("_test_file")
def test_plugin_reports_deselected_tests(pytester):
    result = pytester.runpytest(
        "-p",
        "pytest_bazel._impl.shard",
        "--bazel-shard-index=0",
        "--bazel-total-shards=4",
    )

    result.assert_outcomes(passed=5, deselected=15)


@pytest.mark.usefixtures("_test_file")
@pytest.mark.parametrize(("index", "total"), [(3, 3), (0, 0), (-1, 2)], ids=str)
def test_plugin_rejects_invalid_shard(pytester, index, total):
    result = pytester.runpytest(
        "-p",
        "pytest_bazel._impl.shard",
        f"--bazel-shard-index={index}",
        f"--bazel-total-shards={total}",
    )

    assert result.ret == pytest.ExitCode.USAGE_ERROR


@pytest.mark.usefixtures("_test_file")
def test_bazel_sharding_without_pytest_shard(pytester, tmp_path):
    """Run pytest with the args that pytest_bazel computes for a sharded test."""
    assert importlib.util.find_spec("pytest_shard") is None, (
        "this test must run without pytest-shard to prove it is not needed"
    )

    def args_for_shard(i):
        env = BazelEnv(
            {
                "BAZEL_TEST": "1",
                "TEST_SHARD_INDEX": str(i),
                "TEST_TOTAL_SHARDS": "3",
                "TEST_SHARD_STATUS_FILE": str(tmp_path / f"shard_{i}"),
            }
        )
        return _pytest_args(args=[], env=env)

    shards = _run_shards(pytester, 3, args_for_shard)

    assert sum(len(s) for s in shards) == _NUM_TESTS
    assert len(set().union(*shards)) == _NUM_TESTS


def test_shards_split_what_is_left_after_deselection(pytester):
    pytester.makepyfile("def test_0(): pass\ndef test_1(): pass\ndef test_2(): pass\n")

    results = [
        pytester.runpytest(
            "-p",
            "pytest_bazel._impl.shard",
            f"--bazel-shard-index={i}",
            "--bazel-total-shards=3",
            "-k",
            "not test_1",
        )
        for i in range(3)
    ]

    assert [r.ret for r in results] == [pytest.ExitCode.OK] * 3
    passed = sum(r.parseoutcomes().get("passed", 0) for r in results)
    assert passed == len(["test_0", "test_2"])


def test_empty_shard_passes(pytester):
    num_tests = 2
    pytester.makepyfile("def test_one(): pass\ndef test_two(): pass\n")

    results = [
        pytester.runpytest(
            "-p",
            "pytest_bazel._impl.shard",
            f"--bazel-shard-index={i}",
            "--bazel-total-shards=4",
        )
        for i in range(4)
    ]

    assert [r.ret for r in results] == [pytest.ExitCode.OK] * 4
    assert sum(r.parseoutcomes().get("passed", 0) for r in results) == num_tests


def test_shards_of_a_target_without_tests_fail(pytester):
    pytester.makepyfile("")

    result = pytester.runpytest(
        "-p",
        "pytest_bazel._impl.shard",
        "--bazel-shard-index=1",
        "--bazel-total-shards=4",
    )

    assert result.ret == pytest.ExitCode.NO_TESTS_COLLECTED


if __name__ == "__main__":
    from pytest_bazel import main

    main()
