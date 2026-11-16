"""Explain how to debug tests, as `bazel test` gives them no terminal.

`pytest_bazel._impl.main` loads this plugin under `bazel test`. The debugger would
read from the stdin of the test, which bazel closes, and quit right away, so
fail with a message that says to use `bazel run` instead. breakpoint() is
left alone when PYTHONBREAKPOINT is set.
"""

import os
import sys
from collections.abc import Callable
from typing import Any

import pytest

from pytest_bazel._impl.env import BazelEnv


def _how() -> str:
    target = BazelEnv(os.environ).test_target or "//<package>:<target>"
    return (
        "bazel test gives the test no terminal to debug it in. Run it with "
        f"`bazel run {target} -- --pdb` instead."
    )


_BREAKPOINTHOOK = pytest.StashKey[Callable[..., Any]]()


def _breakpoint(*_args, **_kwargs):
    # Show the breakpoint() call of the test as the place of the error.
    __tracebackhide__ = True
    msg = f"breakpoint() was called. {_how()}"
    raise RuntimeError(msg)


def pytest_configure(config: pytest.Config) -> None:
    """Fail on --pdb and --trace, and on breakpoint() in the tests."""
    for option, name in (("usepdb", "--pdb"), ("trace", "--trace")):
        if config.getoption(option, False):
            msg = f"{name} needs a terminal. {_how()}"
            raise pytest.UsageError(msg)

    # `python -E` and `-I` ignore PYTHONBREAKPOINT.
    if os.environ.get("PYTHONBREAKPOINT") and not sys.flags.ignore_environment:
        # Like pytest, keep the debugger that the user chose, e.g. `0` to
        # ignore breakpoint() or a remote debugger that needs no terminal.
        return

    # pytest sets its own breakpointhook when it starts, replace it.
    config.stash[_BREAKPOINTHOOK] = sys.breakpointhook
    sys.breakpointhook = _breakpoint


def pytest_unconfigure(config: pytest.Config) -> None:
    """Restore the breakpointhook."""
    hook = config.stash.get(_BREAKPOINTHOOK, None)
    if hook is not None:
        sys.breakpointhook = hook
