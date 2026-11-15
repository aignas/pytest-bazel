import importlib
import multiprocessing
import os
import socket
import tempfile
from pathlib import Path

import pytest

from pytest_bazel.main import _remove_tmpdir_alias, _tmpdir_alias

pytestmark = pytest.mark.skipif(os.name != "posix", reason="posix only")

_SUN_PATH_MAX = 104
_PRIVATE_MODE = 0o700
# `/pytest-bazel-XXXXXXXX/tmp` below the alias root.
_MAX_ALIAS_SUFFIX_LEN = 40

# `pytest_bazel.main` is also the name of the function.
_main_module = importlib.import_module("pytest_bazel.main")


@pytest.fixture
def alias_root(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(_main_module, "_ALIAS_ROOT", str(root))
    return root


@pytest.fixture
def long_dir(tmp_path):
    p = tmp_path / ("x" * 80)
    p.mkdir()
    return p


def test_long_tmpdir_gets_a_short_alias(alias_root, long_dir):
    alias = _tmpdir_alias(long_dir)

    assert alias.is_symlink()
    assert alias.resolve() == long_dir.resolve()
    assert alias.parent.parent == alias_root
    assert len(str(alias)) - len(str(alias_root)) < _MAX_ALIAS_SUFFIX_LEN


def test_alias_dir_is_private(alias_root, long_dir):
    alias = _tmpdir_alias(long_dir)

    assert alias.parent.stat().st_mode & 0o777 == _PRIVATE_MODE


def test_each_call_gets_its_own_alias(alias_root, long_dir):
    assert _tmpdir_alias(long_dir) != _tmpdir_alias(long_dir)


def test_short_tmpdir_is_kept(alias_root, tmp_path, monkeypatch):
    monkeypatch.setattr(_main_module, "_MAX_TMPDIR_LEN", len(str(tmp_path)))

    assert _tmpdir_alias(tmp_path) == tmp_path
    assert list(alias_root.iterdir()) == []


def test_falls_back_without_alias_root(alias_root, long_dir):
    alias_root.rmdir()

    assert _tmpdir_alias(long_dir) == long_dir


def test_alias_is_removed_by_its_owner_only(alias_root, long_dir):
    alias = _tmpdir_alias(long_dir)

    _remove_tmpdir_alias(alias, owner_pid=os.getpid() + 1)
    assert alias.is_symlink(), "a forked child must not remove the alias"

    _remove_tmpdir_alias(alias, owner_pid=os.getpid())
    assert not alias.parent.exists()
    assert long_dir.exists(), "only the alias must be removed"


@pytest.mark.skipif("BAZEL_TEST" not in os.environ, reason="needs bazel test")
def test_tmpdir_has_room_for_a_socket():
    """This test runs through pytest_bazel.main, which must have set TMPDIR."""
    tmpdir = Path(os.environ["TMPDIR"])
    assert tmpdir.resolve() == Path(os.environ["TEST_TMPDIR"]).resolve()

    with tempfile.TemporaryDirectory() as d:
        sock_path = str(Path(d) / "listener-abcdefgh")
        assert len(sock_path) < _SUN_PATH_MAX, sock_path
        with socket.socket(socket.AF_UNIX) as s:
            s.bind(sock_path)


@pytest.mark.skipif("BAZEL_TEST" not in os.environ, reason="needs bazel test")
def test_multiprocessing_manager_starts():
    with multiprocessing.Manager() as manager:
        d = manager.dict()
        d["ok"] = True
        assert d["ok"]


if __name__ == "__main__":
    from pytest_bazel import main

    main()
