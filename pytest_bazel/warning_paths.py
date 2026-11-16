"""Make the warnings of the tests useful outside of the bazel sandbox."""

import contextlib
import warnings
from collections.abc import Iterator
from pathlib import Path, PurePath
from typing import Optional


@contextlib.contextmanager
def _warnings_to_file(path: Optional[Path]) -> Iterator[None]:
    """Write the warnings that reach `warnings.showwarning` to `path`, if set.

    Bazel copies TEST_WARNINGS_OUTPUT_FILE to the test results.
    """
    if not path:
        yield
        return

    # Append, as pytest_bazel.warnings_output appends to the same file.
    path.write_text("")
    with path.open("a") as out:

        def showwarning(  # noqa: PLR0913, PLR0917
            message, category, filename, lineno, file=None, line=None
        ):
            out.write(warnings.formatwarning(message, category, filename, lineno, line))
            out.flush()

        original = warnings.showwarning
        warnings.showwarning = showwarning
        try:
            yield
        finally:
            warnings.showwarning = original


def _relative_to_runfiles(filename: str, start: PurePath) -> str:
    """Return `filename` relative to `start` if it is in the runfiles tree.

    `start` is the runfiles root of the main repository, e.g.
    `<runfiles>/_main`, files of other repositories are in its siblings, e.g.
    `<runfiles>/other+/mod.py` becomes `../other+/mod.py`. Any other file, e.g.
    on another drive on Windows, or a name like `<string>`, is returned as it
    is, so that formatting a warning never fails because of its path.
    """
    try:
        path = type(start)(filename)
        if not path.is_absolute():
            return filename
        # Lexical, unlike os.path.relpath it does not fail across drives.
        parts = path.relative_to(start.parent).parts
    except (TypeError, ValueError):
        return filename

    if parts and type(start)(parts[0]) == type(start)(start.name):
        return str(type(start)(*parts[1:]))
    return str(type(start)("..", *parts))


@contextlib.contextmanager
def _relative_warning_paths(start: Path) -> Iterator[None]:
    """Print the paths of warnings relative to the runfiles root under bazel test.

    Python prints the absolute path of the file that issued a warning, which
    under bazel is deep in the sandbox and does not exist after the test. pytest
    uses `warnings.formatwarning` for its warnings summary too. The paths
    relative to `start`, the runfiles root, are the same as the paths in the
    workspace, so editors can open them.
    """
    original = warnings.formatwarning

    def formatwarning(message, category, filename, lineno, line=None):
        filename = _relative_to_runfiles(filename, start)
        return original(message, category, filename, lineno, line)

    warnings.formatwarning = formatwarning
    try:
        yield
    finally:
        warnings.formatwarning = original
