"""`_pytest_args` only computes args, `_prepare` sets up the process."""

import os
import sys

import pytest

from pytest_bazel._impl.main import BazelEnv, _prepare, _pytest_args

pytest_plugins = ["pytester"]


def _sharded(tmp_path):
    return {
        "BAZEL_TEST": "1",
        "TEST_SHARD_INDEX": "0",
        "TEST_TOTAL_SHARDS": "2",
        "TEST_SHARD_STATUS_FILE": str(tmp_path / "status"),
    }


def test_pytest_args_has_no_side_effects(tmp_path):
    _pytest_args(args=[], env=BazelEnv(_sharded(tmp_path)))

    assert not (tmp_path / "status").exists()


def test_prepare_advertises_sharding(tmp_path):
    _prepare(BazelEnv(_sharded(tmp_path)))

    assert (tmp_path / "status").exists()


def test_prepare_without_sharding(tmp_path):
    env = _sharded(tmp_path)
    del env["TEST_TOTAL_SHARDS"]

    _prepare(BazelEnv(env))

    assert not (tmp_path / "status").exists()


def test_prepare_does_nothing_without_bazel_test(tmp_path):
    env = _sharded(tmp_path)
    del env["BAZEL_TEST"]

    _prepare(BazelEnv(env))

    assert not (tmp_path / "status").exists()


@pytest.mark.parametrize(
    ("env", "want"),
    [
        ({"BAZEL_TEST": "1"}, True),
        ({"BAZEL_TEST": "1", "BUILD_WORKSPACE_DIRECTORY": "/ws"}, False),
        ({}, False),
    ],
    ids=["bazel_test", "bazel_run", "no_bazel"],
)
def test_no_bytecode_is_written_under_bazel_test(monkeypatch, env, want):
    monkeypatch.setattr(sys, "dont_write_bytecode", False)

    _prepare(BazelEnv(env))

    assert sys.dont_write_bytecode is want


def test_no_bytecode_next_to_the_tests(pytester, monkeypatch):
    """Python and pytest's assertion rewriting write to __pycache__ otherwise."""
    pytester.makepyfile(test_ok="def test_ok(): assert True\n")
    pytester.makepyfile(helper="VALUE = 1\n")
    pytester.makepyfile(
        test_imports="import helper\ndef test_x(): assert helper.VALUE\n"
    )
    monkeypatch.setenv("BAZEL_TEST", "1")
    monkeypatch.setenv("TEST_TMPDIR", str(pytester.path / "tmp"))
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([str(pytester.path), *sys.path]))
    for var in (
        "XML_OUTPUT_FILE",
        "TEST_UNDECLARED_OUTPUTS_DIR",
        "BUILD_WORKSPACE_DIRECTORY",
    ):
        monkeypatch.delenv(var, raising=False)

    result = pytester.run(sys.executable, "-m", "pytest_bazel", "-p", "no:randomly")

    assert result.ret == 0, result.stdout.str() + result.stderr.str()
    assert not list(pytester.path.rglob("__pycache__"))


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
