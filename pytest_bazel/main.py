"""The main entrypoint for pytest with bazel integration.

The original template code is based on
https://github.com/caseyduquettesc/rules_python_pytest/commit/4c2fc9850d88594b35c7c53d9316f6162088dd13
"""

import atexit
import contextlib
import faulthandler
import importlib.util
import os
import random
import signal
import sys
import tempfile
import threading
import warnings
from collections.abc import Iterator, MutableMapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Optional

import pytest

# Flags that take file paths as value.
_FLAGS_OUTPUTING_FILES = [
    "--report-log",  # pytest-reportlog
    "--json-report-file",  # pytest-json-report
    "--html",  # pytest-html
]


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


def _maybe_path(p) -> Optional[Path]:
    return Path(p) if p else None


def _maybe_int(v: Optional[str]) -> Optional[int]:
    return int(v) if v is not None else None


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


def _keyword_expression(test_filter: str) -> str:
    """Turn the value of `--test_filter` into a pytest `-k` expression.

    `-k` matches each word against the names of a test and of its parents, so
    split the filter into those names:
    * `TestClass.test_fn`, `TestClass::test_fn` -> `TestClass and test_fn`
    * `test_mod.test_fn` -> `test_mod and test_fn`
    * `dir/test_mod.py::test_fn` -> `test_mod.py and test_fn`

    A filter with spaces, e.g. `foo or bar`, is already a `-k` expression.
    """
    if not test_filter or " " in test_filter:
        return test_filter

    path, sep, rest = test_filter.partition("::")
    if sep or "/" in path or path.endswith(".py"):
        # A file or a pytest node id, the module name is the file name.
        names = [PurePosixPath(path).name, *rest.split("::")]
    else:
        names = test_filter.split(".")

    return " and ".join(name for name in names if name)


def _flag(env: MutableMapping[str, str], name: str) -> bool:
    """Read an opt-in flag, which must be `0` or `1` and defaults to `0`."""
    value = env.get(name, "0")
    if value not in ("0", "1"):
        msg = f"{name} must be 0 or 1, got {value!r}"
        raise ValueError(msg)
    return value == "1"


@dataclass
class BazelEnv:
    """The initial conditions environment described in the bazel docs.

    See https://bazel.build/reference/test-encyclopedia#initial-conditions
    """

    env: MutableMapping[str, str]

    @property
    def test_shard_index(self) -> Optional[int]:
        """Return the TEST_SHARD_INDEX value."""
        return _maybe_int(self.env.get("TEST_SHARD_INDEX"))

    @property
    def test_shard_status_file(self) -> Optional[Path]:
        """Return the TEST_SHARD_STATUS_FILE value or None."""
        return _maybe_path(self.env.get("TEST_SHARD_STATUS_FILE"))

    @property
    def test_total_shards(self) -> Optional[int]:
        """Return the TEST_TOTAL_SHARDS value."""
        return _maybe_int(self.env.get("TEST_TOTAL_SHARDS"))

    @property
    def test_random_seed(self) -> int:
        """Return the TEST_RANDOM_SEED value. If zero, it should be interpreted as no value."""
        return int(self.env.get("TEST_RANDOM_SEED", 0))

    @property
    def test_run_number(self) -> int:
        """Return the TEST_RUN_NUMBER value. If zero, then --runs_per_test is likely not used."""
        return int(self.env.get("TEST_RUN_NUMBER", 0))

    @property
    def is_test(self) -> bool:
        """Return the BAZEL_TEST value as a boolean."""
        return "BAZEL_TEST" in self.env

    @property
    def test_package(self) -> Optional[str]:
        """Return the bazel package of TEST_TARGET if it is in the main repository."""
        target = self.env.get("TEST_TARGET", "")
        for prefix in ("@@//", "@//", "//"):
            if target.startswith(prefix):
                return target[len(prefix) :].partition(":")[0] or None

        return None

    @property
    def config_from_package(self) -> bool:
        """Return PYTEST_BAZEL_CONFIG_FROM_PACKAGE as a boolean.

        Off by default, it will be on by default in 1.0.
        """
        return _flag(self.env, "PYTEST_BAZEL_CONFIG_FROM_PACKAGE")

    @property
    def consider_namespace_packages(self) -> bool:
        """Return PYTEST_BAZEL_CONSIDER_NAMESPACE_PACKAGES as a boolean.

        Off by default, it will be on by default in 1.0.
        """
        return _flag(self.env, "PYTEST_BAZEL_CONSIDER_NAMESPACE_PACKAGES")

    @property
    def scope_collection_to_package(self) -> bool:
        """Return PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE as a boolean.

        Off by default, it will be on by default in 1.0.
        """
        return _flag(self.env, "PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE")

    @property
    def test_tmpdir(self) -> Optional[Path]:
        """Return the TEST_TMPDIR value or None if unset."""
        return _maybe_path(self.env.get("TEST_TMPDIR"))

    @property
    def test_undeclared_outputs_dir(self) -> Optional[Path]:
        """Return the TEST_UNDECLARED_OUTPUTS_DIR value or None if unset."""
        return _maybe_path(self.env.get("TEST_UNDECLARED_OUTPUTS_DIR"))

    @property
    def test_timeout(self) -> Optional[int]:
        """Return the TEST_TIMEOUT value in seconds or None if unset."""
        return _maybe_int(self.env.get("TEST_TIMEOUT"))

    @property
    def test_premature_exit_file(self) -> Optional[Path]:
        """Return the TEST_PREMATURE_EXIT_FILE value or None if unset."""
        return _maybe_path(self.env.get("TEST_PREMATURE_EXIT_FILE"))

    @property
    def test_warnings_output_file(self) -> Optional[Path]:
        """Return the TEST_WARNINGS_OUTPUT_FILE value or None if unset."""
        return _maybe_path(self.env.get("TEST_WARNINGS_OUTPUT_FILE"))

    @property
    def test_filter(self) -> str:
        """Return TESTBRIDGE_TEST_ONLY as a `-k` expression, see `_keyword_expression`."""
        return _keyword_expression(self.env.get("TESTBRIDGE_TEST_ONLY", ""))

    @property
    def xml_output_file(self) -> Optional[Path]:
        """Return the XML_OUTPUT_FILE value or None if unset."""
        return _maybe_path(self.env.get("XML_OUTPUT_FILE"))

    @property
    def test_target(self) -> Optional[str]:
        """Return the TEST_TARGET value, e.g. `//foo:bar_test`, or None if unset."""
        return self.env.get("TEST_TARGET") or None

    @property
    def test_runner_fail_fast(self) -> bool:
        """Return the TESTBRIDGE_TEST_RUNNER_FAIL_FAST value as a boolean."""
        return self.env.get("TESTBRIDGE_TEST_RUNNER_FAIL_FAST") == "1"


# AF_UNIX socket paths are limited to 104 bytes on macOS and 108 on Linux.
# Leave room for the names that e.g. `multiprocessing` creates under TMPDIR.
_MAX_TMPDIR_LEN = 60

# Where to create short aliases for long TEST_TMPDIR paths.
_ALIAS_ROOT = "/tmp"


def _remove_tmpdir_alias(alias: Path, owner_pid: int) -> None:
    # Forked children run the parent's atexit handlers too.
    if os.getpid() != owner_pid:
        return
    with contextlib.suppress(OSError):
        alias.unlink()
        alias.parent.rmdir()


def _tmpdir_alias(test_tmpdir: Path) -> Path:
    """Return a short path that points to `test_tmpdir`.

    `bind()` checks the length of the path it is given rather than of the
    resolved path, so a short symlink lets tests bind AF_UNIX sockets under
    TMPDIR while the files still end up in TEST_TMPDIR.

    Returns `test_tmpdir` itself if it is short enough or if no alias can be
    created.
    """
    if os.name != "posix" or len(str(test_tmpdir)) <= _MAX_TMPDIR_LEN:
        return test_tmpdir

    try:
        # A fresh 0700 dir with a random name, so nobody else can swap the link.
        private_dir = Path(tempfile.mkdtemp(prefix="pytest-bazel-", dir=_ALIAS_ROOT))
        alias = private_dir / "tmp"
        alias.symlink_to(test_tmpdir, target_is_directory=True)
    except OSError:
        return test_tmpdir

    atexit.register(_remove_tmpdir_alias, alias, os.getpid())
    return alias


def _set_tmpdir(env: BazelEnv) -> None:
    """Point the temp dir env vars at Bazel's per-test TEST_TMPDIR.

    Bazel does not export TMPDIR for tests, so `tempfile` and anything built on
    it would use the shared system temp dir instead of the test's private one.
    That is non-hermetic and breaks on remote execution workers that mount
    `/tmp` as `noexec`. TMP and TEMP are set for `tempfile` on Windows.

    Long TEST_TMPDIR paths are replaced with a short alias, see `_tmpdir_alias`.
    """
    if not env.is_test or not env.test_tmpdir:
        return

    tmpdir = str(_tmpdir_alias(env.test_tmpdir.absolute()))
    for var in ("TMPDIR", "TMP", "TEMP"):
        env.env[var] = tmpdir

    if env.env is os.environ:
        # `tempfile.gettempdir()` caches its result process-wide.
        tempfile.tempdir = None


def _pytest_version() -> tuple[int, ...]:
    """Return the `(major, minor)` version of pytest, `(0, 0)` before pytest 7.0."""
    # `pytest.version_tuple` is available since pytest 7.0.
    return tuple(getattr(pytest, "version_tuple", (0, 0))[:2])


def _process_args(args: list[str], env: BazelEnv) -> list[str]:
    # pytest < 8.0 runs tests twice if __init__.py is passed explicitly as an argument.
    # Remove any __init__.py file to avoid that.
    # https://github.com/pytest-dev/pytest/issues/9313
    if _pytest_version() < (8, 0):
        args = [
            arg
            for arg in args
            if arg.startswith("-") or Path(arg).name != "__init__.py"
        ]

    # Handle plugins that generate reports - if they are provided with relative paths (via args),
    # re-write it under bazel's test undeclared outputs dir.
    undeclared_output_dir = env.test_undeclared_outputs_dir
    if undeclared_output_dir:
        for i, arg in enumerate(args):
            for flag in _FLAGS_OUTPUTING_FILES:
                if arg.startswith(f"{flag}="):
                    flag_value, _, p = arg.partition("=")
                    if p and not Path(flag_value).is_absolute():
                        args[i] = f"{flag}={undeclared_output_dir}/{p}"

    if not env.test_filter:
        return args

    return [*args, "-k", f"{env.test_filter}"]


def _supports_namespace_packages() -> bool:
    # https://docs.pytest.org/en/stable/reference/reference.html#confval-consider_namespace_packages
    return _pytest_version() >= (8, 1)


def _opt_in_args(env: BazelEnv) -> list[str]:
    """Return the args for the behaviour that is opt-in until 1.0."""
    args: list[str] = []

    if env.consider_namespace_packages and _supports_namespace_packages():
        # Bazel packages usually have no `__init__.py`, so without this pytest
        # names test modules after the closest regular package only, e.g.
        # `foo/numpy/bar_test.py` would become `numpy.bar_test` and shadow the
        # real `numpy`. It is ignored on pytest < 8.1, which has no such option.
        args.extend(["-o", "consider_namespace_packages=true"])

    package = env.test_package

    # pytest looks for config files in the current directory, which is the
    # runfiles root, so it misses e.g. a pytest.ini next to the tests. Pass it
    # explicitly and keep the rootdir, so that test ids and `testpaths` stay
    # relative to the runfiles root. A `-c` in the user args wins.
    config = (
        _find_package_config(package) if env.config_from_package and package else None
    )
    if config:
        args.extend(["-c", str(config), "--rootdir=."])

    # Without args pytest collects everything under the runfiles root, which
    # includes tests of other bazel packages that are pulled in via `deps` or
    # `data`. Limit the collection to the bazel package of the target, pytest
    # only uses `testpaths` if no paths are passed as args.
    if env.scope_collection_to_package and package and Path(package).is_dir():
        args.extend(["-o", f"testpaths={package}"])

    return args


def _pytest_args(*, args: list[str], env: BazelEnv) -> list[str]:
    """Construct pytest args.

    Args:
    ----
        args: the list of extra arguments to pass.
        env: the bazel environment.

    """
    if not env.is_test:
        return args

    pytest_args = [
        # Only needed if users are not specifying
        # build --nolegacy_external_runfiles
        "--ignore=external",
        # The following is a rules_python convention to have the packages extracted in `site-packages` folder, this
        # also means that if the user is using the `py_wheel_library` from `pycross` they may end up with site-packages
        # in it.
        "--ignore-glob=**/site-packages",
        # Avoid loading of the plugin "cacheprovider".
        "-p",
        "no:cacheprovider",
    ]

    if env.xml_output_file:
        pytest_args.append(f"--junitxml={env.xml_output_file}")
        if env.test_target:
            # Name the suite after the target so that merged reports are readable,
            # users can still override it as their args come later.
            pytest_args.extend(["-o", f"junit_suite_name={env.test_target}"])

    # Pass the TEST_TMPDIR to pytest to ensure that everything is in the sandbox. This is to ensure that things get
    # cleaned up correctly in case things are not cleaned up correctly.
    if env.test_tmpdir:
        tmp_dir = env.test_tmpdir / "pytest"
        pytest_args.append(f"--basetemp={tmp_dir}")

    pytest_args.extend(_opt_in_args(env))

    random_seed = env.test_random_seed or env.test_run_number
    if random_seed:
        if importlib.util.find_spec("pytest_randomly"):
            # using pytest-randomly
            pytest_args.append(f"--randomly-seed={random_seed}")
        else:
            random.seed(random_seed)

    if env.test_shard_index is not None and env.test_total_shards is not None:
        # https://bazel.build/reference/test-encyclopedia#test-sharding
        pytest_args.extend(
            [
                "-p",
                "pytest_bazel.shard",
                f"--bazel-shard-index={env.test_shard_index}",
                f"--bazel-total-shards={env.test_total_shards}",
            ]
        )
        if env.test_shard_status_file:
            env.test_shard_status_file.touch(exist_ok=True)

    if env.test_runner_fail_fast:
        pytest_args.append("--exitfirst")

    pytest_args.extend(_process_args(args=args, env=env))
    return pytest_args


@contextlib.contextmanager
def _interrupt_on_sigterm(env: BazelEnv) -> Iterator[None]:
    """Turn the SIGTERM that bazel sends on timeout into a KeyboardInterrupt.

    pytest then prints where the tests were interrupted and writes its
    reports, e.g. the JUnit XML, before bazel kills the process. The stacks of
    all threads are printed too, in case the test hangs in another thread.
    """
    if (
        not env.is_test
        or os.name != "posix"
        or threading.current_thread() is not threading.main_thread()
    ):
        yield
        return

    # pytest redirects the stderr file descriptor while tests run, so keep a
    # copy of it to print to.
    stderr = os.fdopen(os.dup(sys.stderr.fileno()), "w")

    def handler(_signum, _frame):
        timeout = (
            f" after the timeout of {env.test_timeout}s" if env.test_timeout else ""
        )
        print(
            f"\nbazel stopped the test with SIGTERM{timeout}. Stacks of all threads:",
            file=stderr,
            flush=True,
        )
        faulthandler.dump_traceback(file=stderr, all_threads=True)
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, handler)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)
        stderr.close()


def main(
    args=None,
    pytest_main=pytest.main,
    env: Optional[BazelEnv] = None,
) -> int:
    """Execute pytest.

    Args:
    ----
        args: the list of extra arguments to pass. Defaults to sys.argv[1:].
        pytest_main: the function to run instead of `pytest.main`. Used mainly for testing.
        env: the bazel environment. Used mainly for testing, defaults to reading from environment variables.

    """
    env = env or BazelEnv(os.environ)
    _set_tmpdir(env)
    pytest_args = _pytest_args(args=args or sys.argv[1:], env=env)

    print(f"Running pytest.main with: {pytest_args}", file=sys.stderr)

    # Bazel fails the test if this file still exists when the test exits, so
    # that e.g. an `os._exit(0)` in the middle of the run does not pass.
    # It is removed only once pytest has returned.
    premature_exit_file = env.test_premature_exit_file
    if premature_exit_file:
        premature_exit_file.touch()

    warnings_file = env.test_warnings_output_file
    with _interrupt_on_sigterm(env):
        if warnings_file:
            with warnings_file.open("w") as f:
                original_showwarning = warnings.showwarning
                warnings.showwarning = _write_to_file_factory(f)
                try:
                    exit_code = pytest_main(pytest_args)
                finally:
                    warnings.showwarning = original_showwarning
        else:
            exit_code = pytest_main(pytest_args)

    if premature_exit_file:
        premature_exit_file.unlink(missing_ok=True)

    if env.test_filter and exit_code == pytest.ExitCode.NO_TESTS_COLLECTED:
        # If users are filtering out the tests, then exit with a zero if the error code is no-tests collected.
        return 0
    elif exit_code != 0:
        sys.stdout.flush()
        sys.stderr.flush()
        print("Pytest exit code: " + str(exit_code), file=sys.stderr)

    return exit_code
