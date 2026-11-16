"""Read the environment that bazel sets up for tests."""

import importlib.util
from collections.abc import MutableMapping
from pathlib import Path
from typing import Optional

from pytest_bazel.filters import _keyword_expression


def _flag(env: MutableMapping[str, str], name: str) -> bool:
    """Read an opt-in flag, which must be `0` or `1` and defaults to `0`."""
    value = env.get(name, "0")
    if value not in ("0", "1"):
        msg = f"{name} must be 0 or 1, got {value!r}"
        raise ValueError(msg)
    return value == "1"


class _Var:
    """An env var of `BazelEnv`, read when it is accessed."""

    def __init__(self, name: str) -> None:
        self.name = name

    def _get(self, obj: "BazelEnv") -> Optional[str]:
        return obj.env.get(self.name)


class _PathVar(_Var):
    """A path, None if unset or empty."""

    def __get__(self, obj: "BazelEnv", objtype: object = None) -> Optional[Path]:
        value = self._get(obj)
        return Path(value) if value else None


class _IntVar(_Var):
    """An int, None if unset."""

    def __get__(self, obj: "BazelEnv", objtype: object = None) -> Optional[int]:
        value = self._get(obj)
        return int(value) if value is not None else None


class _CountVar(_Var):
    """An int, 0 if unset."""

    def __get__(self, obj: "BazelEnv", objtype: object = None) -> int:
        return int(self._get(obj) or 0)


class _OptIn:
    """An opt-in flag `PYTEST_BAZEL_<NAME>`, off by default and on in 1.0.

    See the "Planned for 1.0" table in README.md.
    """

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = f"PYTEST_BAZEL_{name.upper()}"

    def __get__(self, obj: "BazelEnv", objtype: object = None) -> bool:
        return _flag(obj.env, self.name)


class BazelEnv:
    """The initial conditions environment described in the bazel docs.

    See https://bazel.build/reference/test-encyclopedia#initial-conditions

    Not a dataclass, which takes ~0.4 ms to create when every test imports it.
    """

    def __init__(self, env: MutableMapping[str, str]) -> None:
        """Read the bazel env vars from `env`, e.g. `os.environ`."""
        self.env = env

    def __repr__(self) -> str:
        """Return the repr of a dataclass, as BazelEnv was one."""
        return f"BazelEnv(env={self.env!r})"

    def __eq__(self, other: object) -> bool:
        """Compare the env vars, as a dataclass would."""
        return isinstance(other, BazelEnv) and self.env == other.env

    __hash__ = None  # type: ignore[assignment]  # Like a dataclass, as env changes.

    # Sharding, https://bazel.build/reference/test-encyclopedia#test-sharding
    test_shard_index = _IntVar("TEST_SHARD_INDEX")
    test_shard_status_file = _PathVar("TEST_SHARD_STATUS_FILE")
    test_total_shards = _IntVar("TEST_TOTAL_SHARDS")
    # 0 means unset.
    test_random_seed = _CountVar("TEST_RANDOM_SEED")
    # 0 means unset, i.e. no `--runs_per_test`.
    test_run_number = _CountVar("TEST_RUN_NUMBER")
    test_timeout = _IntVar("TEST_TIMEOUT")

    # Files and directories.
    test_tmpdir = _PathVar("TEST_TMPDIR")
    test_undeclared_outputs_annotations_dir = _PathVar(
        "TEST_UNDECLARED_OUTPUTS_ANNOTATIONS_DIR"
    )
    test_undeclared_outputs_dir = _PathVar("TEST_UNDECLARED_OUTPUTS_DIR")
    test_infrastructure_failure_file = _PathVar("TEST_INFRASTRUCTURE_FAILURE_FILE")
    test_premature_exit_file = _PathVar("TEST_PREMATURE_EXIT_FILE")
    test_warnings_output_file = _PathVar("TEST_WARNINGS_OUTPUT_FILE")
    xml_output_file = _PathVar("XML_OUTPUT_FILE")

    # Opt-in flags of pytest_bazel.
    config_from_package = _OptIn()
    consider_namespace_packages = _OptIn()
    junit_output = _OptIn()
    keep_failed_tmp_path = _OptIn()
    scope_collection_to_package = _OptIn()
    exact_test_filter = _OptIn()

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
    def is_sharded(self) -> bool:
        """Return True if bazel shards the test, see the sharding vars."""
        return self.test_shard_index is not None and self.test_total_shards is not None

    @property
    def test_only(self) -> str:
        """Return TESTBRIDGE_TEST_ONLY, the value of `--test_filter`, or ""."""
        return self.env.get("TESTBRIDGE_TEST_ONLY", "")

    @property
    def uses_exact_test_filter(self) -> bool:
        """Return True if `--test_filter` selects tests by exact names, not `-k`.

        A filter with spaces is a `-k` expression either way, and one without
        any test, e.g. `,`, selects all tests either way.
        """
        return (
            self.exact_test_filter
            and bool(self.test_filter)
            and " " not in self.test_only
        )

    @property
    def test_filter(self) -> str:
        """Return TESTBRIDGE_TEST_ONLY as a `-k` expression, see `_keyword_expression`."""
        return _keyword_expression(self.test_only)

    @property
    def test_target(self) -> Optional[str]:
        """Return the TEST_TARGET value, e.g. `//foo:bar_test`, or None if unset."""
        return self.env.get("TEST_TARGET") or None

    @property
    def test_runner_fail_fast(self) -> bool:
        """Return the TESTBRIDGE_TEST_RUNNER_FAIL_FAST value as a boolean."""
        return self.env.get("TESTBRIDGE_TEST_RUNNER_FAIL_FAST") == "1"


def opt_in_flags() -> list[str]:
    """Return the names of the opt-in env vars, e.g. `PYTEST_BAZEL_JUNIT_OUTPUT`."""
    return [v.name for v in vars(BazelEnv).values() if isinstance(v, _OptIn)]


def _workers_dir(env: BazelEnv) -> Optional[Path]:
    """Return the directory for the stacks of the pytest-xdist workers or None."""
    if not env.test_tmpdir or importlib.util.find_spec("xdist") is None:
        return None
    return env.test_tmpdir / "pytest_bazel_workers"
