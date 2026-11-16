import os
import tempfile
from pathlib import Path

import pytest

from pytest_bazel.env import BazelEnv
from pytest_bazel.tmpdir import _set_tmpdir

_TMP_VARS = ("TMPDIR", "TMP", "TEMP")


def test_sets_tmpdir_vars_under_bazel_test(tmp_path):
    env = BazelEnv({"BAZEL_TEST": "1", "TEST_TMPDIR": str(tmp_path)})

    _set_tmpdir(env)

    for var in _TMP_VARS:
        assert Path(env.env[var]).resolve() == tmp_path.resolve(), var


def test_overrides_inherited_tmpdir(tmp_path):
    env = BazelEnv({"BAZEL_TEST": "1", "TEST_TMPDIR": str(tmp_path), "TMPDIR": "/x"})

    _set_tmpdir(env)

    assert Path(env.env["TMPDIR"]).resolve() == tmp_path.resolve()


@pytest.mark.parametrize(
    "environ",
    [
        pytest.param({"TEST_TMPDIR": "/foo"}, id="not_a_test"),
        pytest.param({"BAZEL_TEST": "1"}, id="no_test_tmpdir"),
    ],
)
def test_noop_outside_of_bazel_test(environ):
    env = BazelEnv(dict(environ))

    _set_tmpdir(env)

    assert env.env == environ


@pytest.mark.skipif("BAZEL_TEST" not in os.environ, reason="needs bazel test")
def test_tempfile_resolves_into_test_tmpdir():
    """This test runs through pytest_bazel.main, which must have set TMPDIR."""
    test_tmpdir = Path(os.environ["TEST_TMPDIR"]).resolve()

    for var in _TMP_VARS:
        assert Path(os.environ[var]).resolve() == test_tmpdir, var

    gettempdir = Path(tempfile.gettempdir()).resolve()
    assert gettempdir == test_tmpdir
    with tempfile.TemporaryDirectory() as d:
        assert test_tmpdir in Path(d).resolve().parents


if __name__ == "__main__":
    from pytest_bazel import main

    main()
