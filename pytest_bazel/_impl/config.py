"""Find the pytest config file of a bazel package, and what it sets."""

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Optional

import pytest

# pytest imports it anyway, and imports e.g. `tomllib` only to read a file.
from _pytest.config.findpaths import load_config_dict_from_file

from pytest_bazel._impl.filters import _split_short_option


def _pytest_version() -> tuple[int, ...]:
    """Return the `(major, minor)` version of pytest, `(0, 0)` before pytest 7.0."""
    # `pytest.version_tuple` is available since pytest 7.0.
    return tuple(getattr(pytest, "version_tuple", (0, 0))[:2])


# The files pytest reads its config from, in the order it looks for them in a
# directory.
# https://docs.pytest.org/en/stable/reference/customize.html#configuration-file-formats
_CONFIG_FILES: tuple[str, ...] = (
    # Since pytest 9.0.
    *(("pytest.toml", ".pytest.toml") if _pytest_version() >= (9, 0) else ()),
    "pytest.ini",
    ".pytest.ini",
    "pyproject.toml",
    "tox.ini",
    "setup.cfg",
)


def _ini_values_or_none(path: Path) -> Optional[dict[str, object]]:
    """Return the options that the file `path` sets, or None if pytest ignores it.

    pytest itself reads the file, as which files and sections count differs
    between pytest versions, e.g. `[tool.pytest]` in pyproject.toml since
    pytest 9.0. A file that pytest fails to read sets nothing, but counts, so
    that pytest reports the error itself.
    """
    try:
        values = load_config_dict_from_file(path)
    except (Exception, pytest.fail.Exception):
        return {}
    if values is None:
        return None
    # The values are `ConfigValue`s since pytest 9.0.
    return {name: getattr(value, "value", value) for name, value in values.items()}


def _first_config(directories: Iterable[Path]) -> Optional[Path]:
    """Return the first pytest config file in `directories`, see `_CONFIG_FILES`."""
    for directory in directories:
        for name in _CONFIG_FILES:
            candidate = directory / name
            if candidate.is_file() and _ini_values_or_none(candidate) is not None:
                return candidate
    return None


def _find_package_config(package: str) -> Optional[Path]:
    """Return the pytest config file for a bazel package or None.

    Look in `package` and its parents like pytest would if it was started in
    `package`. Both are relative to the runfiles root, which is the current
    directory. The runfiles root itself is skipped, pytest finds config files
    there on its own.
    """
    directory = Path(package)
    return _first_config(d for d in (directory, *directory.parents) if d != Path())


def _user_config_arg(args: Sequence[str]) -> Optional[Path]:
    """Return the config file of `-c` or `--config-file` in `args`, the last wins.

    `-c x`, `-cx`, `-c=x`, `-vc x`, `--config-file x` and `--config-file=x`
    are recognised.
    """
    found = None
    for i, arg in enumerate(args):
        if arg.startswith("--config-file="):
            found = arg.partition("=")[2]
            continue
        split = _split_short_option(arg, "c")
        value = split[1] if split else None
        if value is not None:
            found = value
        elif (split or arg == "--config-file") and i + 1 < len(args):
            found = args[i + 1]
    return Path(found) if found else None


def _common_dir(args: Sequence[str]) -> Path:
    """Return the closest common directory of the paths in `args`, like pytest.

    Relative to the current directory, which is the runfiles root. Unlike
    pytest, the values of options, e.g. of `--deselect sub/test_a.py`, count
    too, as telling them apart needs the options of pytest and its plugins.
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
    return _first_config((directory, *directory.parents))


def _config_above_runfiles() -> bool:
    """Return whether pytest could find a config file above the runfiles root.

    In the sandbox nothing is there, but without it, e.g. on Windows, with
    `--spawn_strategy=local` or under `bazel run`, the execroot above the
    runfiles has the files of the workspace root. pytest would then use them
    for its config and its rootdir, unlike in the sandbox.
    """
    names = (*_CONFIG_FILES, "setup.py")
    return any((d / name).is_file() for d in Path.cwd().parents for name in names)


def _ini_values(path: Path) -> dict[str, object]:
    """Return the options that the pytest config file `path` sets."""
    return _ini_values_or_none(path) or {}


def _ini_keys(path: Path) -> set[str]:
    """Return the names of the options that the pytest config file `path` sets."""
    return set(_ini_values(path))


def _ini_paths(value: object) -> list[str]:
    """Return the paths of an option like `testpaths`, a list in toml files."""
    if isinstance(value, str):
        # Like pytest, which splits the values of `args` options like a shell.
        import shlex  # noqa: PLC0415

        return shlex.split(value)
    if isinstance(value, list):
        return [str(item) for item in value]
    return []
