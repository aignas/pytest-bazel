"""The main entrypoint for pytest with bazel integration.

The original template code is based on
https://github.com/caseyduquettesc/rules_python_pytest/commit/4c2fc9850d88594b35c7c53d9316f6162088dd13
"""

import os
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pytest

# Flags that take file paths as value.
_FLAGS_OUTPUTING_FILES = [
    "--report-log",  # pytest-reportlog
    "--json-report-file",  # pytest-json-report
    "--html",  # pytest-html
]


def _supports_sharding() -> bool:
    try:
        import pytest_shard as _  # noqa: F401

        return True
    except ImportError:
        return False


def _write_to_file_factory(out_file):
    """Return a function that used to replace the warnings.showwarning function.

    This is used to write everything to a file that bazel specifies.
    """

    def _fn(  # noqa: PLR0913
        message, category, filename, lineno, file=sys.stderr, line=None
    ):
        out_file.write(
            warnings.formatwarning(message, category, filename, lineno, line)
        )

    return _fn


def _maybe_path(p) -> Optional[Path]:
    return Path(p) if p else None


@dataclass
class BazelEnv:
    """The initial conditions environment described in the bazel docs.

    See https://bazel.build/reference/test-encyclopedia#initial-conditions
    """

    env: Dict[str, str]

    @property
    def test_shard_index(self) -> int:
        """Return the TEST_SHARD_INDEX value."""
        return int(self.env.get("TEST_SHARD_INDEX") or 0)

    @property
    def test_shard_status_file(self) -> Optional[Path]:
        """Return the TEST_SHARD_STATUS_FILE value or None."""
        return _maybe_path(self.env.get("TEST_SHARD_STATUS_FILE"))

    @property
    def test_total_shards(self) -> int:
        """Return the TEST_TOTAL_SHARDS value."""
        return int(self.env.get("TEST_TOTAL_SHARDS") or 0)

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
    def test_tmpdir(self) -> Optional[Path]:
        """Return the TEST_TMPDIR value or None if unset."""
        return _maybe_path(self.env.get("TEST_TMPDIR"))

    @property
    def test_undeclared_outputs_dir(self) -> Optional[Path]:
        """Return the TEST_UNDECLARED_OUTPUTS_DIR value or None if unset."""
        return _maybe_path(self.env.get("TEST_UNDECLARED_OUTPUTS_DIR"))

    @property
    def test_warnings_output_file(self) -> Optional[Path]:
        """Return the TEST_WARNINGS_OUTPUT_FILE value or None if unset."""
        return _maybe_path(self.env.get("TEST_WARNINGS_OUTPUT_FILE"))

    @property
    def test_filter(self) -> str:
        """Return the TESTBRIDGE_TEST_ONLY value after substituting `.` with `::`."""
        test_filter = self.env.get("TESTBRIDGE_TEST_ONLY", "")
        if not test_filter:
            return ""

        if not test_filter[0].isupper():
            # --test_filter=test_module.test_fn or --test_filter=test_module/test_file.py
            return test_filter

        # TestClass.test_fn -> TestClass::test_fn
        return test_filter.replace(".", "::")

    @property
    def xml_output_file(self) -> Optional[Path]:
        """Return the XML_OUTPUT_FILE value or None if unset."""
        return _maybe_path(self.env.get("XML_OUTPUT_FILE"))

    @property
    def test_runner_fail_fast(self) -> bool:
        """Return the TESTBRIDGE_TEST_RUNNER_FAIL_FAST value as a boolean."""
        return self.env.get("TESTBRIDGE_TEST_RUNNER_FAIL_FAST") == "1"


def _process_args(args: List[str], env: BazelEnv) -> List[str]:
    # pytest < 8.0 runs tests twice if __init__.py is passed explicitly as an argument.
    # Remove any __init__.py file to avoid that.
    # pytest.version_tuple is available since pytest 7.0
    # https://github.com/pytest-dev/pytest/issues/9313
    if not hasattr(pytest, "version_tuple") or pytest.version_tuple < (8, 0):
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


def _pytest_args(*, args: List[str], env: BazelEnv) -> List[str]:
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

    # Pass the TEST_TMPDIR to pytest to ensure that everything is in the sandbox. This is to ensure that things get
    # cleaned up correctly in case things are not cleaned up correctly.
    if env.test_tmpdir:
        tmp_dir = env.test_tmpdir / "pytest"
        pytest_args.append(f"--basetemp={tmp_dir}")

    random_seed = env.test_random_seed or env.test_run_number
    if random_seed:
        pytest_args.append(f"--randomly-seed={random_seed}")  # using pytest-randomly

    # Handle test sharding - requires pytest-shard plugin.
    if env.test_shard_index and env.test_total_shards:
        # https://bazel.build/reference/test-encyclopedia#test-sharding
        pytest_args.append(f"--shard-id={env.test_shard_index}")
        pytest_args.append(f"--num-shards={env.test_total_shards}")
        if env.test_shard_status_file and _supports_sharding():
            env.test_shard_status_file.touch(exist_ok=True)

    if env.test_runner_fail_fast:
        pytest_args.append("--exitfirst")

    pytest_args.extend(_process_args(args=args, env=env))
    return pytest_args


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
    pytest_args = _pytest_args(args=args or sys.argv[1:], env=env)

    warnings_file = env.test_warnings_output_file
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

    if env.test_filter and exit_code == pytest.ExitCode.NO_TESTS_COLLECTED:
        # If users are filtering out the tests, then exit with a zero if the error code is no-tests collected.
        return 0
    elif exit_code != 0:
        print("Pytest exit code: " + str(exit_code), file=sys.stderr)
        print("Ran pytest.main with " + str(pytest_args), file=sys.stderr)

    return exit_code
