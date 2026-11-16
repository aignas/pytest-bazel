"""Point the temp dir of the tests at the TEST_TMPDIR of bazel."""

import atexit
import contextlib
import os
import tempfile
from pathlib import Path

from pytest_bazel.env import BazelEnv

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
