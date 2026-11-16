"""Find the pytest config file of a bazel package, and what it sets."""

import configparser
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:  # pytest depends on tomli before Python 3.11.
    import tomli as tomllib

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


def _user_config_arg(args: Sequence[str]) -> Optional[Path]:
    """Return the config file of `-c` or `--config-file` in `args`, the last wins."""
    found = None
    for i, arg in enumerate(args):
        if arg in ("-c", "--config-file") and i + 1 < len(args):
            found = args[i + 1]
        elif arg.startswith("--config-file="):
            found = arg.partition("=")[2]
        elif arg.startswith("-c") and not arg.startswith("--") and len(arg) > len("-c"):
            found = arg[len("-c") :]
    return Path(found) if found else None


def _common_dir(args: Sequence[str]) -> Path:
    """Return the closest common directory of the paths in `args`, like pytest.

    Relative to the current directory, which is the runfiles root.
    """
    dirs = []
    for arg in args:
        if arg.startswith("-"):
            continue
        path = Path(arg.partition("::")[0])
        if path.exists():
            dirs.append(path if path.is_dir() else path.parent)
    if not dirs:
        return Path()

    common = []
    for parts in zip(*(d.parts for d in dirs)):
        if any(part != parts[0] for part in parts):
            break
        common.append(parts[0])
    return Path(*common)


def _pytest_config_file(args: Sequence[str]) -> Optional[Path]:
    """Return the config file that pytest uses for `args`, or None.

    Like pytest, a `-c` wins, else look from the common directory of the
    paths in `args` up to the runfiles root. pytest would look further up,
    but nothing above the runfiles root belongs to the test.
    """
    user_config = _user_config_arg(args)
    if user_config:
        return user_config

    directory = _common_dir(args)
    if directory.is_absolute():
        return None
    while True:
        for name in _CONFIG_FILES:
            candidate = directory / name
            if candidate.is_file() and _is_pytest_config(candidate):
                return candidate
        if directory == Path():
            return None
        directory = directory.parent


def _ini_keys(path: Path) -> set[str]:
    """Return the names of the options that the pytest config file `path` sets.

    An unreadable file sets nothing, pytest reports the error itself.
    """
    try:
        if path.suffix == ".toml":
            tool = tomllib.loads(path.read_text()).get("tool", {})
            pytest_config = tool.get("pytest", {})
            return set(pytest_config.get("ini_options", pytest_config))

        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.read_string(path.read_text())
        section = "tool:pytest" if path.name == "setup.cfg" else "pytest"
        return set(parser[section]) if parser.has_section(section) else set()
    except (OSError, ValueError, configparser.Error):
        return set()
