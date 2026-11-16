"""Write the warnings that pytest records to TEST_WARNINGS_OUTPUT_FILE.

`pytest_bazel._impl.main` loads this plugin when bazel sets the file. pytest
records the warnings of the tests with `warnings.catch_warnings`, so they
never reach `warnings.showwarning`, which `main` redirects to the file for
the warnings outside of pytest.
"""

import warnings
from pathlib import Path
from typing import IO

import pytest

_NAME = "pytest_bazel_warnings_output"


class _Writer:
    def __init__(self, out: IO[str]) -> None:
        self.out = out

    def pytest_warning_recorded(self, warning_message: warnings.WarningMessage) -> None:
        self.out.write(
            warnings.formatwarning(
                str(warning_message.message),
                warning_message.category,
                warning_message.filename,
                warning_message.lineno,
                warning_message.line,
            )
        )
        self.out.flush()


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add the option for the file."""
    group = parser.getgroup("bazel", "Bazel integration")
    group.addoption(
        "--bazel-warnings-file",
        metavar="FILE",
        help="File to append the warnings to, TEST_WARNINGS_OUTPUT_FILE.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Write the warnings, in the main process only with pytest-xdist."""
    path = config.getoption("bazel_warnings_file")
    # pytest-xdist passes the warnings of the workers on to the main process.
    if path and not hasattr(config, "workerinput"):
        # Not the locale encoding, which cannot encode every warning, e.g. on
        # Windows.
        out = Path(path).open(  # noqa: SIM115, closed in pytest_unconfigure
            "a", encoding="utf-8", errors="backslashreplace"
        )
        config.pluginmanager.register(_Writer(out), _NAME)


def pytest_unconfigure(config: pytest.Config) -> None:
    """Stop writing the warnings."""
    writer = config.pluginmanager.get_plugin(_NAME)
    if isinstance(writer, _Writer):
        config.pluginmanager.unregister(writer)
        writer.out.close()
