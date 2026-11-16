"""Select the tests of `--test_filter` by their exact names.

`pytest_bazel.main` loads this plugin with PYTEST_BAZEL_EXACT_TEST_FILTER=1.
A `-k` expression matches substrings of the names of a test and of its
parents, so `--test_filter=test_add` also runs `test_add_many`, and any test
in `test_add.py`.
"""

from collections.abc import Sequence

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
    *dirs, module = path.split("/")
    # Like `PurePosixPath.with_suffix("")`, but this runs for every test.
    dot = module.rfind(".")
    if 0 < dot < len(module) - 1:
        module = module[:dot]
    return [*dirs, module, *rest]


def _is_subsequence(wanted: Sequence[str], names: Sequence[str]) -> bool:
    remaining = iter(names)
    return all(any(name == want for name in remaining) for want in wanted)


def _matches_path(test_filter: str, nodeid: str) -> bool:
    """Match a directory, a file or a node id, e.g. `pkg/test_mod.py::TestA`.

    The path may start at any directory of the path of the test.
    """
    start = nodeid.find(test_filter)
    while start != -1:
        end = start + len(test_filter)
        if (start == 0 or nodeid[start - 1] == "/") and (
            end == len(nodeid) or nodeid.startswith(("::", "[", "/"), end)
        ):
            return True
        start = nodeid.find(test_filter, start + 1)
    return False


class _Filter:
    """A `--test_filter`, parsed once to match many tests."""

    def __init__(self, test_filter: str) -> None:
        # A path, e.g. `pkg/sub` or `test_mod.py::TestA`, without a trailing /.
        self.paths: list[str] = []
        # The names of `a.b` or `A::b`, which must be names of the test in order.
        self.names: list[list[str]] = []
        for part in _split_filters(test_filter):
            path = part.partition("::")[0]
            if "/" in path or path.endswith(".py"):
                self.paths.append(part.rstrip("/"))
            else:
                self.names.append(
                    [w for name in part.split("::") for w in _split(name, ".")]
                )

    def __call__(self, nodeid: str) -> bool:
        if any(_matches_path(path, nodeid) for path in self.paths):
            return True
        # Each name of a match is in the node id, which rules out most tests
        # quickly.
        candidates = [
            wanted for wanted in self.names if all(name in nodeid for name in wanted)
        ]
        if not candidates:
            return False
        names = _names(nodeid)
        # The name of a parametrized test matches with and without its parameters.
        function = names[-1].partition("[")[0]
        plain = [*names[:-1], function] if function != names[-1] else names
        return any(
            _is_subsequence(wanted, names) or _is_subsequence(wanted, plain)
            for wanted in candidates
        )


def matches(test_filter: str, nodeid: str) -> bool:
    """Return whether the `--test_filter` selects the test `nodeid`."""
    return _Filter(test_filter)(nodeid)


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Deselect the tests that the filter does not select."""
    test_filter = config.getoption("bazel_test_filter")
    if not test_filter:
        return
    selects = _Filter(test_filter)
    keep = []
    deselected = []
    for item in items:
        (keep if selects(item.nodeid) else deselected).append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = keep
