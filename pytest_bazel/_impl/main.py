"""The main entrypoint for pytest with bazel integration.

The original template code is based on
https://github.com/caseyduquettesc/rules_python_pytest/commit/4c2fc9850d88594b35c7c53d9316f6162088dd13
"""

import contextlib
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Optional, Union

import pytest

from pytest_bazel._impl.config import (
    _common_dir,
    _config_above_runfiles,
    _find_package_config,
    _ini_keys,
    _ini_paths,
    _ini_values,
    _pytest_config_file,
    _pytest_version,
    _user_config_arg,
)
from pytest_bazel._impl.env import BazelEnv, _workers_dir, flag_errors
from pytest_bazel._impl.filters import _with_keyword_expression
from pytest_bazel._impl.sigterm import _interrupt_on_sigterm
from pytest_bazel._impl.tmpdir import _clean_kept_basetemp, _set_tmpdir
from pytest_bazel._impl.warning_paths import _relative_warning_paths, _warnings_to_file

# Flags that take file paths as value.
_FLAGS_OUTPUTTING_FILES = (
    "--report-log",  # pytest-reportlog
    "--json-report-file",  # pytest-json-report
    "--html",  # pytest-html
)


# pytest exit codes that mean pytest itself failed, rather than the tests.
# https://docs.pytest.org/en/stable/reference/exit-codes.html
_INFRASTRUCTURE_FAILURES: dict[int, str] = {
    pytest.ExitCode.INTERNAL_ERROR: "e.g. because a plugin or a conftest.py failed",
    pytest.ExitCode.USAGE_ERROR: "e.g. because of an unknown flag or a missing plugin",
}


def _in_outputs_dir(path: str, outputs_dir: Path) -> str:
    """Return a relative report `path` in `outputs_dir`, keep an absolute one."""
    if not path or Path(path).is_absolute():
        return path
    return str(outputs_dir / path)


def _report_path_args(args: list[str], outputs_dir: Path) -> list[str]:
    """Put the relative report paths of `args`, e.g. `--html=r.html`, in `outputs_dir`.

    Both `--html=r.html` and `--html r.html` are handled.
    """
    result = []
    flag_before = False
    for arg in args:
        flag, sep, path = arg.partition("=")
        if flag_before:
            result.append(_in_outputs_dir(arg, outputs_dir))
        elif sep and flag in _FLAGS_OUTPUTTING_FILES:
            result.append(f"{flag}={_in_outputs_dir(path, outputs_dir)}")
        else:
            result.append(arg)
        flag_before = arg in _FLAGS_OUTPUTTING_FILES
    return result


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
        args = _report_path_args(args, undeclared_output_dir)

    if env.uses_exact_test_filter:
        return [
            *args,
            "-p",
            "pytest_bazel._impl.exact_filter",
            f"--bazel-test-filter={env.test_only}",
        ]

    if not env.test_filter:
        return args

    return _with_keyword_expression(args, env.test_filter)


def _kept_basetemp(env: BazelEnv) -> Optional[Path]:
    """Return the basetemp in the bazel outputs to keep failed tmp_paths in."""
    outputs_dir = env.test_undeclared_outputs_dir
    if env.keep_failed_tmp_path and outputs_dir and _pytest_version() >= (7, 3):
        return outputs_dir / "pytest"
    return None


def _basetemp_args(env: BazelEnv) -> list[str]:
    """Return the args for where pytest creates `tmp_path` and friends."""
    kept = _kept_basetemp(env)
    if kept:
        # Bazel copies the undeclared outputs to bazel-testlogs, so keep the
        # `tmp_path` of failed tests there to help debugging them, see
        # `tmp_path_retention_policy` in `_ini_defaults`.
        return [f"--basetemp={kept}"]

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
                "pytest_bazel._impl.annotations",
                f"--bazel-annotations-dir={annotations_dir}",
            ]
        )

    warnings_file = env.test_warnings_output_file
    if warnings_file:
        args.extend(
            [
                "-p",
                "pytest_bazel._impl.warnings_output",
                f"--bazel-warnings-file={warnings_file}",
            ]
        )

    workers_dir = _workers_dir(env)
    if workers_dir:
        args.extend(
            ["-p", "pytest_bazel._impl.workers", f"--bazel-workers-dir={workers_dir}"]
        )

    return args


def _package_config(env: BazelEnv) -> Optional[Path]:
    """Return the config file of the package of the target to pass, or None.

    pytest looks for config files in the current directory, which is the
    runfiles root, so it misses e.g. a pytest.ini next to the tests. It is
    passed explicitly with `--rootdir=.`, so that test ids stay relative to the
    runfiles root, see `_package_testpaths` for its `testpaths`.
    """
    package = env.test_package
    if not env.config_from_package or not package:
        return None
    return _find_package_config(package)


def _package_testpaths(config: Path) -> Optional[str]:
    """Return the `testpaths` of the package `config`, relative to its directory.

    With `--rootdir=.`, pytest would look for them in the runfiles root, but
    they are written for running pytest next to the config file.
    """
    paths = _ini_paths(_ini_values(config).get("testpaths"))
    if not paths:
        return None
    # Imported here, as only tests with a package config need it.
    import shlex  # noqa: PLC0415

    return shlex.join(str(config.parent / path) for path in paths)


def _ini_defaults(env: BazelEnv) -> dict[str, str]:
    """Return the ini options that pytest_bazel sets unless the config file does."""
    defaults = {}

    if env.xml_output_file and env.test_target:
        # Name the suite after the target so that merged reports are readable.
        defaults["junit_suite_name"] = env.test_target

    if _kept_basetemp(env):
        # Only the `tmp_path` of failed tests, the others are not needed.
        defaults["tmp_path_retention_policy"] = "failed"

    if env.junit_output and env.xml_output_file:
        # CI shows the JUnit XML, which only has the output of the tests with
        # `junit_logging`. Leave it out for passing tests to keep it small.
        defaults["junit_logging"] = "all"
        defaults["junit_log_passing_tests"] = "false"

    # https://docs.pytest.org/en/stable/reference/reference.html#confval-consider_namespace_packages
    if env.consider_namespace_packages and _pytest_version() >= (8, 1):
        # Bazel packages usually have no `__init__.py`, so without this pytest
        # names test modules after the closest regular package only, e.g.
        # `foo/numpy/bar_test.py` would become `numpy.bar_test` and shadow the
        # real `numpy`. It is ignored on pytest < 8.1, which has no such option.
        defaults["consider_namespace_packages"] = "true"

    # Without args pytest collects everything under the runfiles root, which
    # includes tests of other bazel packages that are pulled in via `deps` or
    # `data`. Limit the collection to the bazel package of the target, pytest
    # only uses `testpaths` if no paths are passed as args.
    package = env.test_package
    if env.scope_collection_to_package and package and Path(package).is_dir():
        defaults["testpaths"] = package

    return defaults


def _ini_default_args(
    args: list[str], env: BazelEnv, package_config: Optional[Path]
) -> list[str]:
    """Return `-o` args for the ini defaults that the user did not configure.

    `-o` wins over the config file, so leave out the options that the config
    file that pytest uses for `args` sets. A `-o` in `args` comes later and
    wins anyway. `package_config` is the config file passed with
    `--rootdir=.`, see `_package_config`.
    """
    config = _pytest_config_file(args)
    configured = _ini_keys(config) if config else set()
    defaults = _ini_defaults(env)
    package = env.test_package
    # A config file outside of the package, e.g. in the runfiles root, is
    # shared by many targets, its `testpaths` are not for this one.
    shared = bool(package and config and not config.parent.is_relative_to(package))

    if (
        config is not None
        and config == package_config
        and "testpaths" in configured
        and not (shared and "testpaths" in defaults)
    ):
        testpaths = _package_testpaths(config)
        if testpaths:
            defaults["testpaths"] = testpaths
            configured.discard("testpaths")
    if shared:
        configured.discard("testpaths")

    result = []
    for name, value in defaults.items():
        if name not in configured:
            result.extend(["-o", f"{name}={value}"])
    return result


def _random_seed(env: BazelEnv) -> int:
    """Return the seed for the random order and data of the tests, 0 for none."""
    return env.test_random_seed or env.test_run_number


def _empty_config(env: BazelEnv) -> Optional[Path]:
    """Return the empty config file that keeps pytest in the runfiles, see below."""
    if not env.is_test or not env.test_tmpdir:
        return None
    return env.test_tmpdir / "pytest_bazel_empty.ini"


def _hermetic_args(args: list[str], env: BazelEnv) -> list[str]:
    """Return the args that keep pytest from using files above the runfiles root.

    Without the sandbox, pytest finds e.g. the pytest.ini of the workspace in
    the execroot above the runfiles, see `_config_above_runfiles`. Then pass
    what pytest would find in the sandbox: the config file in the runfiles,
    or an empty one and the rootdir it would use without a config file.
    """
    if _user_config_arg(args) or not _config_above_runfiles():
        return []
    config = _pytest_config_file(args)
    if config:
        # pytest derives the rootdir and confcutdir from it, as in the sandbox.
        return ["-c", str(config)]
    empty = _empty_config(env)
    if not empty or not empty.is_file():
        # `_prepare` creates it, without it pytest would fail.
        return []
    rootdir = _common_dir(args)
    return ["-c", str(empty), f"--rootdir={rootdir}", f"--confcutdir={rootdir}"]


def _prepare(env: BazelEnv) -> None:
    """Set up the process for the args of `_pytest_args`, which has no side effects."""
    _set_tmpdir(env)
    if not env.is_test:
        return

    if not env.is_bazel_run:
        # Tests may only write to TEST_TMPDIR and the outputs, but Python and
        # the assertion rewriting of pytest write .pyc files next to the
        # sources in the runfiles. They still read the precompiled ones.
        sys.dont_write_bytecode = True

    empty = _empty_config(env)
    if empty:
        empty.parent.mkdir(parents=True, exist_ok=True)
        empty.write_text("")

    if env.is_sharded:
        status_file = env.test_shard_status_file
        if status_file:
            # Tell bazel that the test supports sharding, see `_pytest_args`.
            status_file.touch(exist_ok=True)


def _pytest_args(*, args: list[str], env: BazelEnv) -> list[str]:
    """Construct pytest args.

    Args:
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
        pytest_args.extend(["-p", "pytest_bazel._impl.debugging"])

    if env.xml_output_file:
        pytest_args.append(f"--junitxml={env.xml_output_file}")

    pytest_args.extend(_basetemp_args(env))

    package_config = _package_config(env)
    # `-c` would only load the conftest.py files below the config file, e.g.
    # not the one of the workspace root, so keep loading them from the runfiles
    # root. A `--confcutdir` of the user comes later and wins.
    opt_in_args = (
        ["-c", str(package_config), "--rootdir=.", "--confcutdir=."]
        if package_config
        else _hermetic_args(args, env)
    )
    pytest_args.extend(opt_in_args)
    # The `-c` of the opt-in args, if any, comes before the one of the user.
    pytest_args.extend(_ini_default_args([*opt_in_args, *args], env, package_config))

    random_seed = _random_seed(env)
    if random_seed:
        pytest_args.extend(
            [
                "-p",
                "pytest_bazel._impl.random_seed",
                f"--bazel-random-seed={random_seed}",
            ]
        )

    pytest_args.extend(_plugin_args(env))

    if env.is_sharded:
        # https://bazel.build/reference/test-encyclopedia#test-sharding
        pytest_args.extend(
            [
                "-p",
                "pytest_bazel._impl.shard",
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


def _usage_error(env: BazelEnv, errors: list[str]) -> int:
    """Report `errors` in the setup of pytest_bazel, like pytest reports its own."""
    text = "".join(f"pytest_bazel: {error}\n" for error in errors)
    sys.stderr.write(text)
    failure_file = env.test_infrastructure_failure_file
    if failure_file:
        failure_file.write_text(text)
    return pytest.ExitCode.USAGE_ERROR


def main(
    args: Optional[list[str]] = None,
    pytest_main: Callable[[list[str]], Union[int, pytest.ExitCode]] = pytest.main,
    env: Optional[BazelEnv] = None,
) -> int:
    """Execute pytest.

    Args:
        args: the list of extra arguments to pass. Defaults to sys.argv[1:].
        pytest_main: the function to run instead of `pytest.main`. Used mainly for testing.
        env: the bazel environment. Used mainly for testing, defaults to reading from environment variables.

    """
    env = env or BazelEnv(os.environ)
    errors = flag_errors(env)
    if errors:
        # Before reading them, which would fail with a traceback.
        return _usage_error(env, errors)
    _prepare(env)
    if args is None:
        args = sys.argv[1:]
    pytest_args = _pytest_args(args=args, env=env)

    print(f"Running pytest.main with: {pytest_args}", file=sys.stderr)

    # Bazel fails the test if this file still exists when the test exits, so
    # that e.g. an `os._exit(0)` in the middle of the run does not pass.
    # It is removed only once pytest has returned.
    premature_exit_file = env.test_premature_exit_file
    if premature_exit_file:
        premature_exit_file.touch()

    with contextlib.ExitStack() as stack:
        stack.enter_context(_interrupt_on_sigterm(env))
        if env.is_test and not env.is_bazel_run:
            # Only under `bazel test`, where the sandbox is gone after the test.
            # With `bazel run`, which also sets BAZEL_TEST for test targets, or
            # without bazel the absolute paths exist and work from any directory.
            stack.enter_context(_relative_warning_paths(Path.cwd()))
        stack.enter_context(_warnings_to_file(env.test_warnings_output_file))
        exit_code = pytest_main(pytest_args)

    kept_basetemp = _kept_basetemp(env)
    if kept_basetemp:
        _clean_kept_basetemp(kept_basetemp, passed=exit_code == pytest.ExitCode.OK)

    if premature_exit_file:
        premature_exit_file.unlink(missing_ok=True)

    _report_infrastructure_failure(env, exit_code)

    if env.test_filter and exit_code == pytest.ExitCode.NO_TESTS_COLLECTED:
        how = (
            f"{env.test_only!r} by exact names"
            if env.uses_exact_test_filter
            else f"-k {env.test_filter!r}"
        )
        # Pass, as `bazel test //... --test_filter=x` filters every target,
        # but say so, as a typo in the filter would pass too.
        print(
            f"pytest_bazel: --test_filter selected no tests ({how})",
            file=sys.stderr,
        )
        return 0
    if exit_code != pytest.ExitCode.OK:
        sys.stdout.flush()
        sys.stderr.flush()
        print(f"Pytest exit code: {exit_code!s}", file=sys.stderr)

    return exit_code
