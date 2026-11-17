"""Keep the paths in the tracebacks of failed tests easy to open in an editor.

`pytest_bazel._impl.main` loads this plugin under `bazel test`. pytest prints
the paths in tracebacks relative to the directory it started in, the runfiles
root, which for the main repository is the same as the workspace root. But

* once a test changed the current directory, e.g. with `monkeypatch.chdir`,
  pytest prints them as absolute paths into the bazel sandbox, which is gone
  after the test, and
* `--tb=line` always prints the absolute path of where the test failed.
"""

import os
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from pytest_bazel._impl.warning_paths import _relative_to_runfiles

if TYPE_CHECKING:
    # `pluggy._Result` before pluggy 1.1.
    from pluggy import Result


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(
    item: pytest.Item,
) -> Generator[None, "Result[pytest.TestReport]", None]:
    """Build the report of a test phase in the directory pytest started in."""
    start = item.config.invocation_params.dir
    try:
        cwd = Path.cwd()
    except OSError:
        # The test removed the current directory, there is no way back.
        cwd = None

    moved = cwd != start
    if moved:
        os.chdir(start)
    try:
        outcome = yield
    finally:
        if moved and cwd is not None:
            os.chdir(cwd)

    _relative_crash_path(outcome.get_result(), start)


def _relative_crash_path(report: pytest.TestReport, start: Path) -> None:
    """Make the location of the failure relative, which `--tb=line` prints."""
    crash: Any = getattr(report.longrepr, "reprcrash", None)
    path = getattr(crash, "path", None)
    if isinstance(path, str):
        crash.path = _relative_to_runfiles(path, start)
