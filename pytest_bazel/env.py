"""Read the environment that bazel sets up for tests."""

import importlib.util
from collections.abc import MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pytest_bazel.filters import _keyword_expression


def _maybe_path(p) -> Optional[Path]:
    return Path(p) if p else None


def _maybe_int(v: Optional[str]) -> Optional[int]:
    return int(v) if v is not None else None


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
        """Return the BAZEL_TEST value as a boolean.

        Bazel sets it for `bazel test`, and for `bazel run` of a test target.
        """
        return "BAZEL_TEST" in self.env

    @property
    def is_bazel_run(self) -> bool:
        """Return True under `bazel run`, which has a terminal."""
        return "BUILD_WORKSPACE_DIRECTORY" in self.env

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
    def junit_output(self) -> bool:
        """Return PYTEST_BAZEL_JUNIT_OUTPUT as a boolean.

        Off by default, it will be on by default in 1.0.
        """
        return _flag(self.env, "PYTEST_BAZEL_JUNIT_OUTPUT")

    @property
    def keep_failed_tmp_path(self) -> bool:
        """Return PYTEST_BAZEL_KEEP_FAILED_TMP_PATH as a boolean.

        Off by default, it will be on by default in 1.0.
        """
        return _flag(self.env, "PYTEST_BAZEL_KEEP_FAILED_TMP_PATH")

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
    def test_undeclared_outputs_annotations_dir(self) -> Optional[Path]:
        """Return the TEST_UNDECLARED_OUTPUTS_ANNOTATIONS_DIR value or None if unset."""
        return _maybe_path(self.env.get("TEST_UNDECLARED_OUTPUTS_ANNOTATIONS_DIR"))

    @property
    def test_undeclared_outputs_dir(self) -> Optional[Path]:
        """Return the TEST_UNDECLARED_OUTPUTS_DIR value or None if unset."""
        return _maybe_path(self.env.get("TEST_UNDECLARED_OUTPUTS_DIR"))

    @property
    def test_infrastructure_failure_file(self) -> Optional[Path]:
        """Return the TEST_INFRASTRUCTURE_FAILURE_FILE value or None if unset."""
        return _maybe_path(self.env.get("TEST_INFRASTRUCTURE_FAILURE_FILE"))

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


def _workers_dir(env: BazelEnv) -> Optional[Path]:
    """Return the directory for the stacks of the pytest-xdist workers or None."""
    if not env.test_tmpdir or importlib.util.find_spec("xdist") is None:
        return None
    return env.test_tmpdir / "pytest_bazel_workers"
