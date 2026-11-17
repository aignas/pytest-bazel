"""Find the pytest config file of a bazel package, and what it sets."""

import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Optional

import pytest


def _pytest_version() -> tuple[int, ...]:
    """Return the `(major, minor)` version of pytest, `(0, 0)` before pytest 7.0."""
    # `pytest.version_tuple` is available since pytest 7.0.
    return tuple(getattr(pytest, "version_tuple", (0, 0))[:2])


# The files pytest reads its config from, in the order it looks for them in a
# directory, and the sections they need to have to count.
# https://docs.pytest.org/en/stable/reference/customize.html#configuration-file-formats
_CONFIG_FILES: dict[str, Optional[tuple[str, ...]]] = {
    # Since pytest 9.0.
    **(
        {"pytest.toml": None, ".pytest.toml": None}
        if _pytest_version() >= (9, 0)
        else {}
    ),
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

    # pytest reads config files as UTF-8, only the section names matter here.
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = {line.strip() for line in text.splitlines()}
    return any(section in lines for section in sections)


def _first_config(directories: Iterable[Path]) -> Optional[Path]:
    """Return the first pytest config file in `directories`, see `_CONFIG_FILES`."""
    for directory in directories:
        for name in _CONFIG_FILES:
            candidate = directory / name
            if candidate.is_file() and _is_pytest_config(candidate):
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


def _toml_values(path: Path) -> dict[str, object]:
    # Imported here, as most tests have no config file and it takes ~4 ms.
    if sys.version_info >= (3, 11):
        import tomllib  # noqa: PLC0415
    else:  # pytest depends on tomli before Python 3.11.
        import tomli as tomllib  # noqa: PLC0415

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    # Like pytest, which reads `[pytest]` from pytest.toml, and `[tool.pytest]`
    # or `[tool.pytest.ini_options]` from pyproject.toml and other toml files.
    # pytest 9.2 also reads `[pytest]` from a toml file passed with `-c`.
    if path.name in ("pytest.toml", ".pytest.toml"):
        return dict(data.get("pytest", {}))
    pytest_config = data.get("tool", {}).get("pytest", {})
    values = dict(pytest_config.get("ini_options", pytest_config))
    if path.name != "pyproject.toml":
        values = {**data.get("pytest", {}), **values}
    return values


def _ini_file_values(path: Path) -> dict[str, object]:
    # Imported here, as most tests have no config file.
    import configparser  # noqa: PLC0415

    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read_string(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, configparser.Error):
        return {}
    # Like pytest, which reads `[tool:pytest]` from any `.cfg` file.
    section = "tool:pytest" if path.suffix == ".cfg" else "pytest"
    return dict(parser[section]) if parser.has_section(section) else {}


def _ini_values(path: Path) -> dict[str, object]:
    """Return the options that the pytest config file `path` sets.

    An unreadable file sets nothing, pytest reports the error itself.
    """
    return _toml_values(path) if path.suffix == ".toml" else _ini_file_values(path)


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
