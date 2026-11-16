"""Run only the part of the collected tests that belongs to this Bazel shard.

`pytest_bazel.main` loads this plugin when Bazel shards a test, i.e. when it
sets `TEST_SHARD_INDEX` and `TEST_TOTAL_SHARDS`. See
https://bazel.build/reference/test-encyclopedia#test-sharding
"""

from collections.abc import Sequence

import pytest

# Set when this shard got no tests, but other shards did.
_EMPTY_SHARD = pytest.StashKey[bool]()

# The key in the `workeroutput` of pytest-xdist, as the workers collect the
# tests, but the main process sets the exit code.
_WORKER_EMPTY_SHARD = "pytest_bazel_empty_shard"


def select_shard(node_ids: Sequence[str], index: int, total: int) -> set[str]:
    """Return the node ids that the shard `index` out of `total` should run.

    Every shard sorts the node ids in the same way and takes every `total`-th
    one, starting at `index`. That only depends on the set of tests, so all
    shards agree on the split, and shard sizes differ by at most one.
    """
    return set(sorted(node_ids)[index::total])


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add the sharding options."""
    group = parser.getgroup("bazel", "Bazel integration")
    group.addoption(
        "--bazel-shard-index",
        type=int,
        default=0,
        metavar="INDEX",
        help="Shard to run, the value of TEST_SHARD_INDEX.",
    )
    group.addoption(
        "--bazel-total-shards",
        type=int,
        default=1,
        metavar="TOTAL",
        help="Number of shards, the value of TEST_TOTAL_SHARDS.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Fail early on an invalid shard."""
    index = config.getoption("bazel_shard_index")
    total = config.getoption("bazel_total_shards")
    if total < 1 or not 0 <= index < total:
        msg = f"invalid shard {index} of {total} shards"
        raise pytest.UsageError(msg)


# trylast: split what is left after e.g. `-k` and `-m` deselected tests, so
# that no shard gets only deselected tests.
@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Deselect the tests that other shards run."""
    selected = select_shard(
        [item.nodeid for item in items],
        index=config.getoption("bazel_shard_index"),
        total=config.getoption("bazel_total_shards"),
    )

    keep = []
    other_shards = []
    for item in items:
        if item.nodeid in selected:
            keep.append(item)
        else:
            other_shards.append(item)

    if other_shards:
        config.hook.pytest_deselected(items=other_shards)
        items[:] = keep

    empty = bool(other_shards) and not keep
    config.stash[_EMPTY_SHARD] = empty
    workeroutput = getattr(config, "workeroutput", None)
    if workeroutput is not None:
        workeroutput[_WORKER_EMPTY_SHARD] = empty


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node, error) -> None:
    """Pass the empty shard of a pytest-xdist worker on to the main process."""
    if getattr(node, "workeroutput", {}).get(_WORKER_EMPTY_SHARD):
        node.config.stash[_EMPTY_SHARD] = True


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Pass a shard that got no tests because there are more shards than tests.

    pytest exits with NO_TESTS_COLLECTED otherwise, which fails the whole
    bazel test. A target without any tests still fails in every shard.
    """
    if exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED and session.config.stash.get(
        _EMPTY_SHARD, False
    ):
        session.exitstatus = pytest.ExitCode.OK
