"""
The main entrypoint for pytest with bazel integration.

The original template code is based on
https://github.com/caseyduquettesc/rules_python_pytest/commit/4c2fc9850d88594b35c7c53d9316f6162088dd13
"""

import sys
import os
import warnings
from pathlib import Path

import pytest


def _write_to_file_factory(out_file):
    """Return a function that used to overwrite the warnings.showwarning to write to the file we specified"""

    def bazel_collect_warning(
        message, category, filename, lineno, file=sys.stderr, line=None
    ):
        out_file.write(
            warnings.formatwarning(message, category, filename, lineno, line)
        )

    return bazel_collect_warning


def main(args=sys.argv[1:], pytest_main=pytest.main, sys_exit=sys.exit):
    """The main entrypoint wrapping pytest to be used in py_console_script_binary."""
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

    # pytest < 8.0 runs tests twice if __init__.py is passed explicitly as an argument.
    # Remove any __init__.py file to avoid that.
    # pytest.version_tuple is available since pytest 7.0
    # https://github.com/pytest-dev/pytest/issues/9313
    if not hasattr(pytest, "version_tuple") or pytest.version_tuple < (8, 0):
        args = [
            arg
            for arg in args
            if arg.startswith("-") or os.path.basename(arg) != "__init__.py"
        ]

    if os.environ.get("XML_OUTPUT_FILE"):
        pytest_args.append(
            "--junitxml={xml_output_file}".format(
                xml_output_file=os.environ.get("XML_OUTPUT_FILE")
            )
        )

    # Pass the TEST_TMPDIR to pytest to ensure that everything is in the sandbox. This is to ensure that things get
    # cleaned up correctly in case things are not cleaned up correctly.
    tmp_dir = os.environ.get("TEST_TMPDIR")
    if tmp_dir:
        tmp_dir = Path(tmp_dir) / "pytest"
        pytest_args.append(f"--basetemp={tmp_dir}")

    random_seed = os.environ.get("TEST_RANDOM_SEED") or os.environ.get(
        "TEST_RUN_NUMBER"
    )
    if random_seed:
        pytest_args.append(f"--randomly-seed={random_seed}")

    # Handle test sharding - requires pytest-shard plugin.
    if os.environ.get("TEST_SHARD_INDEX") and os.environ.get("TEST_TOTAL_SHARDS"):
        pytest_args.append(
            "--shard-id={shard_id}".format(shard_id=os.environ.get("TEST_SHARD_INDEX"))
        )
        pytest_args.append(
            "--num-shards={num_shards}".format(
                num_shards=os.environ.get("TEST_TOTAL_SHARDS")
            )
        )
        if os.environ.get("TEST_SHARD_STATUS_FILE"):
            open(os.environ["TEST_SHARD_STATUS_FILE"], "a").close()

    # Handle plugins that generate reports - if they are provided with relative paths (via args),
    # re-write it under bazel's test undeclared outputs dir.
    if os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR"):
        undeclared_output_dir = os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR")

        # Flags that take file paths as value.
        path_flags = [
            "--report-log",  # pytest-reportlog
            "--json-report-file",  # pytest-json-report
            "--html",  # pytest-html
        ]
        for i, arg in enumerate(args):
            for flag in path_flags:
                if arg.startswith(f"{flag}="):
                    arg_split = arg.split("=", 1)
                    if len(arg_split) == 2 and not os.path.isabs(arg_split[1]):
                        args[i] = f"{flag}={undeclared_output_dir}/{arg_split[1]}"

    if os.environ.get("TESTBRIDGE_TEST_ONLY"):
        # TestClass.test_fn -> TestClass::test_fn
        module_name = os.environ["TESTBRIDGE_TEST_ONLY"].replace(".", "::")

        # If the test filter does not start with a class-like name, then use test filtering instead
        # --test_filter=test_fn
        if not module_name[0].isupper():
            pytest_args.extend(args)
            pytest_args.append("-k={filter}".format(filter=module_name))
        else:
            # --test_filter=TestClass.test_fn
            # Add test filter to path-like args
            for arg in args:
                if not arg.startswith("--"):
                    # Maybe a src file? Add test class/method selection to it. Not sure if this will work if the
                    # symbol can't be found in the test file.
                    arg = "{arg}::{module_fn}".format(arg=arg, module_fn=module_name)
                pytest_args.append(arg)
    else:
        pytest_args.extend(args)

    warnings_file = os.environ.get("TEST_WARNINGS_OUTPUT_FILE")
    if warnings_file:
        with open(warnings_file, "w") as f:
            warnings.showwarning = _write_to_file_factory(f)
            exit_code = pytest_main(pytest_args)
    else:
        exit_code = pytest_main(pytest_args)

    if exit_code != 0:
        print("Pytest exit code: " + str(exit_code), file=sys.stderr)
        print("Ran pytest.main with " + str(pytest_args), file=sys.stderr)
        sys_exit(exit_code)

    # By default python programs exit with 0, so no need for this, it just makes the testing harder
