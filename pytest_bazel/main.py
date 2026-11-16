"""The main entrypoint for pytest with bazel integration.

The original template code is based on
https://github.com/caseyduquettesc/rules_python_pytest/commit/4c2fc9850d88594b35c7c53d9316f6162088dd13
"""

import contextlib
import importlib.util
import os
import random
import sys
import warnings
from pathlib import Path
from typing import Optional

import pytest

from pytest_bazel.config import _find_package_config
from pytest_bazel.env import BazelEnv, _workers_dir
from pytest_bazel.sigterm import _interrupt_on_sigterm
from pytest_bazel.tmpdir import _set_tmpdir
from pytest_bazel.warning_paths import _relative_warning_paths, _write_to_file_factory

__all__ = ["BazelEnv", "main"]

# Flags that take file paths as value.
_FLAGS_OUTPUTING_FILES = [
    "--report-log",  # pytest-reportlog
    "--json-report-file",  # pytest-json-report
    "--html",  # pytest-html
]


# pytest exit codes that mean pytest itself failed, rather than the tests.
# https://docs.pytest.org/en/stable/reference/exit-codes.html
_INFRASTRUCTURE_FAILURES = {
    pytest.ExitCode.INTERNAL_ERROR: "e.g. because a plugin or a conftest.py failed",
    pytest.ExitCode.USAGE_ERROR: "e.g. because of an unknown flag or a missing plugin",
}


def _pytest_version() -> tuple[int, ...]:
    """Return the `(major, minor)` version of pytest, `(0, 0)` before pytest 7.0."""
    # `pytest.version_tuple` is available since pytest 7.0.
    return tuple(getattr(pytest, "version_tuple", (0, 0))[:2])


def _report_path_arg(arg: str, outputs_dir: Path) -> str:
    """Put a relative report path of `arg`, e.g. `--html=r.html`, in `outputs_dir`."""
    flag, sep, path = arg.partition("=")
    if not sep or flag not in _FLAGS_OUTPUTING_FILES:
        return arg
    if not path or Path(path).is_absolute():
        return arg
    return f"{flag}={outputs_dir / path}"


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
        args = [_report_path_arg(arg, undeclared_output_dir) for arg in args]

    if not env.test_filter:
        return args

    return [*args, "-k", f"{env.test_filter}"]


def _supports_namespace_packages() -> bool:
    # https://docs.pytest.org/en/stable/reference/reference.html#confval-consider_namespace_packages
    return _pytest_version() >= (8, 1)


def _basetemp_args(env: BazelEnv) -> list[str]:
    """Return the args for where pytest creates `tmp_path` and friends."""
    outputs_dir = env.test_undeclared_outputs_dir
    if env.keep_failed_tmp_path and outputs_dir and _pytest_version() >= (7, 3):
        # Bazel copies the undeclared outputs to bazel-testlogs, so keep the
        # `tmp_path` of failed tests there to help debugging them.
        return [
            f"--basetemp={outputs_dir / 'pytest'}",
            "-o",
            "tmp_path_retention_policy=failed",
        ]

    # Keep everything in the sandbox, bazel cleans TEST_TMPDIR up.
    if env.test_tmpdir:
        return [f"--basetemp={env.test_tmpdir / 'pytest'}"]

    return []


def _plugin_args(env: BazelEnv) -> list[str]:
    """Return the args that load the plugins of pytest_bazel."""
    args = []
    annotations_dir = env.test_undeclared_outputs_annotations_dir
    if annotations_dir:
        args.extend(
            [
                "-p",
                "pytest_bazel.annotations",
                f"--bazel-annotations-dir={annotations_dir}",
            ]
        )

    workers_dir = _workers_dir(env)
    if workers_dir:
        args.extend(
            ["-p", "pytest_bazel.workers", f"--bazel-workers-dir={workers_dir}"]
        )

    return args


def _opt_in_args(env: BazelEnv) -> list[str]:
    """Return the args for the behaviour that is opt-in until 1.0."""
    args: list[str] = []

    if env.junit_output and env.xml_output_file:
        # CI shows the JUnit XML, which only has the output of the tests with
        # `junit_logging`. Leave it out for passing tests to keep it small.
        args.extend(["-o", "junit_logging=all", "-o", "junit_log_passing_tests=false"])

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


def _random_seed(env: BazelEnv) -> int:
    """Return the seed for the random order and data of the tests, 0 for none."""
    return env.test_random_seed or env.test_run_number


def _has_pytest_randomly() -> bool:
    return importlib.util.find_spec("pytest_randomly") is not None


def _prepare(env: BazelEnv) -> None:
    """Set up the process for the args of `_pytest_args`, which has no side effects."""
    _set_tmpdir(env)
    if not env.is_test:
        return

    random_seed = _random_seed(env)
    if random_seed and not _has_pytest_randomly():
        # pytest-randomly seeds `random` itself, see `_pytest_args`.
        random.seed(random_seed)

    if env.test_shard_index is not None and env.test_total_shards is not None:
        status_file = env.test_shard_status_file
        if status_file:
            # Tell bazel that the test supports sharding, see `_pytest_args`.
            status_file.touch(exist_ok=True)


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

    if not env.is_bazel_run:
        # Explain how to debug, as tests get no terminal under bazel test.
        pytest_args.extend(["-p", "pytest_bazel.debugging"])

    if env.xml_output_file:
        pytest_args.append(f"--junitxml={env.xml_output_file}")
        if env.test_target:
            # Name the suite after the target so that merged reports are readable,
            # users can still override it as their args come later.
            pytest_args.extend(["-o", f"junit_suite_name={env.test_target}"])

    pytest_args.extend(_basetemp_args(env))

    pytest_args.extend(_opt_in_args(env))

    random_seed = _random_seed(env)
    if random_seed and _has_pytest_randomly():
        pytest_args.append(f"--randomly-seed={random_seed}")

    pytest_args.extend(_plugin_args(env))

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

    if env.test_runner_fail_fast:
        pytest_args.append("--exitfirst")

    pytest_args.extend(_process_args(args=args, env=env))
    return pytest_args


def _report_infrastructure_failure(env: BazelEnv, exit_code: int) -> None:
    """Tell bazel when pytest itself failed rather than the tests.

    Bazel keeps the file as `test.infrastructure_failure` in bazel-testlogs and
    lists it in the build event protocol, so that e.g. CI can tell a broken
    setup from a failing test.
    """
    failure_file = env.test_infrastructure_failure_file
    if not failure_file or exit_code not in _INFRASTRUCTURE_FAILURES:
        return

    reason = _INFRASTRUCTURE_FAILURES[exit_code]
    failure_file.write_text(
        f"pytest could not run the tests ({pytest.ExitCode(exit_code).name}), {reason}. "
        "See the test log for details.\n"
    )


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
    _prepare(env)
    pytest_args = _pytest_args(args=args or sys.argv[1:], env=env)

    print(f"Running pytest.main with: {pytest_args}", file=sys.stderr)

    # Bazel fails the test if this file still exists when the test exits, so
    # that e.g. an `os._exit(0)` in the middle of the run does not pass.
    # It is removed only once pytest has returned.
    premature_exit_file = env.test_premature_exit_file
    if premature_exit_file:
        premature_exit_file.touch()

    warnings_file = env.test_warnings_output_file
    # Only under `bazel test`, where the sandbox is gone after the test. With
    # `bazel run`, which also sets BAZEL_TEST for test targets, or without bazel
    # the absolute paths exist and work from any directory.
    relative_warning_paths = (
        _relative_warning_paths(Path.cwd())
        if env.is_test and not env.is_bazel_run
        else contextlib.nullcontext()
    )
    with _interrupt_on_sigterm(env), relative_warning_paths:
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

    _report_infrastructure_failure(env, exit_code)

    if env.test_filter and exit_code == pytest.ExitCode.NO_TESTS_COLLECTED:
        # If users are filtering out the tests, then exit with a zero if the error code is no-tests collected.
        return 0
    elif exit_code != 0:
        sys.stdout.flush()
        sys.stderr.flush()
        print("Pytest exit code: " + str(exit_code), file=sys.stderr)

    return exit_code
