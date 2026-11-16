"""Make the warnings of the tests useful outside of the bazel sandbox."""

import contextlib
import sys
import warnings
from collections.abc import Iterator
from pathlib import Path, PurePath


def _write_to_file_factory(out_file):
    """Return a function that used to replace the warnings.showwarning function.

    This is used to write everything to a file that bazel specifies.
    """

    def _fn(  # noqa: PLR0913, PLR0917
        message, category, filename, lineno, file=sys.stderr, line=None
    ):
        out_file.write(
            warnings.formatwarning(message, category, filename, lineno, line)
        )

    return _fn


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
