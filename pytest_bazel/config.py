"""Find the pytest config file of a bazel package."""

from pathlib import Path
from typing import Optional

# The files pytest reads its config from, in the order it looks for them in a
# directory, and the sections they need to have to count.
# https://docs.pytest.org/en/stable/reference/customize.html#configuration-file-formats
_CONFIG_FILES = {
    "pytest.ini": None,
    ".pytest.ini": None,
    "pyproject.toml": ("[tool.pytest.ini_options]", "[tool.pytest]"),
    "tox.ini": ("[pytest]",),
    "setup.cfg": ("[tool:pytest]",),
}


def _is_pytest_config(path: Path) -> bool:
    sections = _CONFIG_FILES[path.name]
    if sections is None:
        return True

    lines = {line.strip() for line in path.read_text().splitlines()}
    return any(section in lines for section in sections)


def _find_package_config(package: str) -> Optional[Path]:
    """Return the pytest config file for a bazel package or None.

    Look in `package` and its parents like pytest would if it was started in
    `package`. Both are relative to the runfiles root, which is the current
    directory. The runfiles root itself is skipped, pytest finds config files
    there on its own.
    """
    directory = Path(package)
    while directory != Path():
        for name in _CONFIG_FILES:
            candidate = directory / name
            if candidate.is_file() and _is_pytest_config(candidate):
                return candidate
        directory = directory.parent

    return None
