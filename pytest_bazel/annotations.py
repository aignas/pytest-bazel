"""Write a summary of the test results as a bazel test annotation.

`pytest_bazel.main` loads this plugin when bazel sets
`TEST_UNDECLARED_OUTPUTS_ANNOTATIONS_DIR`. Bazel adds the `*.part` files in
that directory to `bazel-testlogs/<target>/test.outputs_manifest/ANNOTATIONS`.
See https://bazel.build/reference/test-encyclopedia#test-interaction-filesystem
"""

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

# The order in which outcomes are listed in the summary.
_OUTCOMES = ("failed", "error", "passed", "skipped", "xfailed", "xpassed", "deselected")

# Keep the annotation short, it is meant to be read at a glance.
_MAX_FAILURES = 20


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add the option for the annotations directory."""
    group = parser.getgroup("bazel", "Bazel integration")
    group.addoption(
        "--bazel-annotations-dir",
        metavar="DIR",
        help="Directory to write the summary annotation to, the value of "
        "TEST_UNDECLARED_OUTPUTS_ANNOTATIONS_DIR.",
    )


def summary(stats: Mapping[str, Sequence[object]]) -> str:
    """Return the annotation text for the terminal reporter `stats`."""
    counts = [f"{len(stats[o])} {o}" for o in _OUTCOMES if stats.get(o)]
    lines = ["pytest: " + (", ".join(counts) or "no tests ran")]

    failures = []
    for outcome in ("failed", "error"):
        for report in stats.get(outcome, []):
            line = f"{outcome.upper()} {getattr(report, 'nodeid', report)}"
            if line not in failures:
                failures.append(line)

    lines.extend(failures[:_MAX_FAILURES])
    if len(failures) > _MAX_FAILURES:
        lines.append(f"... and {len(failures) - _MAX_FAILURES} more, see the test log")

    return "\n".join(lines) + "\n"


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, config: pytest.Config
) -> None:
    """Write the summary annotation."""
    directory = config.getoption("bazel_annotations_dir")
    if not directory:
        return

    text = summary(terminalreporter.stats)
    (Path(directory) / "pytest_bazel.part").write_text(text)
