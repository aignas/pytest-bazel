"""What keeps pytest_bazel fast, checked without timings, which would be flaky.

`bazel run //dev/benchmark` measures the timings, see README.md.
"""

import dataclasses
import os
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

from pytest_bazel._impl import exact_filter
from pytest_bazel._impl.env import BazelEnv

# Imported only when a pytest config file is read, as most tests have none.
_LAZY_MODULES = ("configparser", "tomllib", "tomli")


def test_import_does_not_load_the_config_parsers():
    # pytest itself is needed anyway, only what pytest_bazel adds counts.
    code = (
        "import sys, pytest; before = set(sys.modules); "
        "import pytest_bazel._impl.main; "
        "print(' '.join(sorted(set(sys.modules) - before)))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
        capture_output=True,
        text=True,
        check=True,
    )

    loaded = set(result.stdout.split())
    assert loaded, "nothing was imported, the check is broken"
    assert not loaded & set(_LAZY_MODULES), sorted(loaded)


def test_bazel_env_is_a_plain_class():
    """A dataclass takes ~0.4 ms to create, which every test would pay."""
    assert not dataclasses.is_dataclass(BazelEnv)


class _Counter:
    def __init__(self, fn):
        self.fn = fn
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.fn(*args, **kwargs)


def _collect(test_filter, nodeids):
    # Stand-ins for the pytest objects that the hook uses.
    config: Any = SimpleNamespace(
        getoption=lambda _: test_filter,
        hook=SimpleNamespace(pytest_deselected=lambda items: None),
    )
    items: Any = [SimpleNamespace(nodeid=nodeid) for nodeid in nodeids]
    exact_filter.pytest_collection_modifyitems(config, items)
    return [item.nodeid for item in items]


_NODEIDS = [f"pkg{i % 10}/test_mod{i % 7}.py::test_{i}" for i in range(1000)]


def test_exact_filter_is_parsed_once(monkeypatch):
    split = _Counter(exact_filter._split_filters)
    monkeypatch.setattr(exact_filter, "_split_filters", split)

    selected = _collect("test_1,test_2,pkg3/test_mod3.py", _NODEIDS)

    assert selected
    assert split.calls == 1


def test_exact_filter_rules_out_tests_by_substring(monkeypatch):
    """Only tests that contain every name of the filter get split into names."""
    names = _Counter(exact_filter._names)
    monkeypatch.setattr(exact_filter, "_names", names)

    selected = _collect("test_123", _NODEIDS)

    assert selected == ["pkg3/test_mod4.py::test_123"]
    assert names.calls == 1


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
