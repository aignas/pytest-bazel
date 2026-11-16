"""Select the tests of `--test_filter` by their exact names.

`pytest_bazel.main` loads this plugin with PYTEST_BAZEL_EXACT_TEST_FILTER=1.
A `-k` expression matches substrings of the names of a test and of its
parents, so `--test_filter=test_add` also runs `test_add_many`, and any test
in `test_add.py`.
"""

from collections.abc import Sequence
from pathlib import PurePosixPath

import pytest

from pytest_bazel.filters import _split, _split_filters


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add the option for the filter."""
    group = parser.getgroup("bazel", "Bazel integration")
    group.addoption(
        "--bazel-test-filter",
        metavar="FILTER",
        help="Select tests by name, the value of TESTBRIDGE_TEST_ONLY.",
    )


def _names(nodeid: str) -> list[str]:
    """Return the names of a test and its parents, e.g. `pkg.test_mod.TestA.test_b`."""
    path, *rest = nodeid.split("::")
    return [*PurePosixPath(path).with_suffix("").parts, *rest]


def _is_subsequence(wanted: Sequence[str], names: Sequence[str]) -> bool:
    remaining = iter(names)
    return all(any(name == want for name in remaining) for want in wanted)


def _matches_names(test_filter: str, nodeid: str) -> bool:
    """Match `a.b` or `A::b` against the names of the test, in order.

    The name of a parametrized test matches with and without its parameters.
    """
    wanted = [w for part in test_filter.split("::") for w in _split(part, ".")]
    names = _names(nodeid)
    function = names[-1].partition("[")[0]
    return _is_subsequence(wanted, names) or _is_subsequence(
        wanted, [*names[:-1], function]
    )


def _matches_path(test_filter: str, nodeid: str) -> bool:
    """Match a directory, a file or a node id, e.g. `pkg/test_mod.py::TestA`.

    The path may start at any directory of the path of the test.
    """
    test_filter = test_filter.rstrip("/")
    ends = (f"{test_filter}::", f"{test_filter}[", f"{test_filter}/")
    for start in range(len(nodeid)):
        if start and nodeid[start - 1] != "/":
            continue
        rest = nodeid[start:]
        if rest == test_filter or rest.startswith(ends):
            return True
    return False


def matches(test_filter: str, nodeid: str) -> bool:
    """Return whether the `--test_filter` selects the test `nodeid`."""
    for part in _split_filters(test_filter):
        path = part.partition("::")[0]
        if "/" in path or path.endswith(".py"):
            if _matches_path(part, nodeid):
                return True
        elif _matches_names(part, nodeid):
            return True
    return False


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Deselect the tests that the filter does not select."""
    test_filter = config.getoption("bazel_test_filter")
    if not test_filter:
        return
    keep = []
    deselected = []
    for item in items:
        (keep if matches(test_filter, item.nodeid) else deselected).append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = keep
