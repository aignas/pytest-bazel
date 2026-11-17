"""Make pytest-xdist workers work well under bazel test.

`pytest_bazel._impl.main` loads this plugin under `bazel test` when pytest-xdist is
installed. It

* lets the stacks of the workers be printed when bazel times out the test, as
  the test usually hangs in a worker rather than in the main process, and
* warns when `-n auto` starts more workers than bazel reserved CPUs for.
"""

import faulthandler
import os
import signal
import time
from collections.abc import Sequence
from pathlib import Path
from typing import IO, TYPE_CHECKING, Optional

import pytest

if TYPE_CHECKING:
    from xdist.workermanage import WorkerController

# How long to wait for the workers to write their stacks.
_DUMP_TIMEOUT = 2.0

_STACKS_FILE = pytest.StashKey[IO[str]]()


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add the option for the directory that the workers write their stacks to."""
    group = parser.getgroup("bazel", "Bazel integration")
    group.addoption(
        "--bazel-workers-dir",
        metavar="DIR",
        help="Directory for the stacks of the pytest-xdist workers.",
    )


def _worker_id(config: pytest.Config) -> Optional[str]:
    workerinput = getattr(config, "workerinput", None)
    return workerinput["workerid"] if workerinput else None


def pytest_configure(config: pytest.Config) -> None:
    """Dump the stacks of this worker to a file on SIGTERM or SIGUSR1.

    Bazel usually sends SIGTERM to the whole process group on timeout, so the
    worker dumps its stacks before it stops. SIGUSR1 is for the main process to
    ask for them in case only it got the SIGTERM.
    """
    directory = config.getoption("bazel_workers_dir")
    worker_id = _worker_id(config)
    if not directory or not worker_id or not hasattr(signal, "SIGUSR1"):
        return

    path = Path(directory) / f"{os.getpid()}-{worker_id}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    stacks = path.open("w")
    config.stash[_STACKS_FILE] = stacks
    faulthandler.register(signal.SIGUSR1, file=stacks, all_threads=True)
    # chain=True: the worker still stops on SIGTERM.
    faulthandler.register(signal.SIGTERM, file=stacks, all_threads=True, chain=True)


def pytest_unconfigure(config: pytest.Config) -> None:
    """Stop dumping the stacks on signals, and remove the file of this worker.

    `stop_workers` kills the process of every file, so a file left behind
    could name the PID of an unrelated process later.
    """
    stacks = config.stash.get(_STACKS_FILE, None)
    if stacks is None:
        return
    faulthandler.unregister(signal.SIGUSR1)
    faulthandler.unregister(signal.SIGTERM)
    stacks.close()
    Path(stacks.name).unlink(missing_ok=True)


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node: "WorkerController", error: Optional[object]) -> None:
    """Remove the file of a worker that crashed.

    A crashed worker does not get to `pytest_unconfigure`. Other workers
    remove their file themselves, as they may still hang after the session,
    e.g. on a thread, and a timeout should print their stacks then.
    """
    directory = node.config.getoption("bazel_workers_dir")
    if error is None or not directory:
        return
    for path in Path(directory).glob(f"*-{node.gateway.id}.txt"):
        path.unlink(missing_ok=True)


# tryfirst: the hook stops at the first result, and the one of xdist returns one.
@pytest.hookimpl(optionalhook=True, tryfirst=True)
def pytest_xdist_auto_num_workers(config: pytest.Config) -> None:
    """Warn that `-n auto` does not know how many CPUs bazel reserved."""
    if os.environ.get("PYTEST_XDIST_AUTO_NUM_WORKERS"):
        return
    # xdist calls this while pytest is configured, where warnings.warn is lost.
    config.issue_config_time_warning(
        pytest.PytestConfigWarning(
            "`-n auto` starts a pytest-xdist worker for every CPU of the machine, "
            "but bazel only reserves 1 CPU for a test. Reserve more with "
            'tags = ["cpu:N"] and set PYTEST_XDIST_AUTO_NUM_WORKERS=N in the env '
            "of the test."
        ),
        stacklevel=2,
    )


def _size(path: Path) -> Optional[int]:
    """Return the size of the stack file `path`, None if the worker removed it.

    Workers remove their file when they stop, see `pytest_unconfigure`.
    """
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return None


def _wait_for(paths: Sequence[Path], timeout: float) -> None:
    """Wait until all `paths` have content or are gone, or `timeout` seconds pass."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and any(_size(p) == 0 for p in paths):
        time.sleep(0.05)


def _pid_and_worker(path: Path) -> tuple[int, str]:
    """Return the PID and the worker id of a `<pid>-<worker id>.txt` file."""
    pid, _, worker_id = path.stem.partition("-")
    return int(pid), worker_id


def _signal(path: Path, signum: int) -> bool:
    """Send `signum` to the worker of `path`, return False if it is gone."""
    try:
        os.kill(_pid_and_worker(path)[0], signum)
    except (OSError, ValueError):
        # The worker is gone, e.g. pytest-xdist restarted it.
        return False
    return True


def stop_workers(directory: Path, out: IO[str]) -> None:
    """Print the stacks of the workers that registered in `directory`, then kill them.

    Bazel kills the test with SIGKILL a few seconds after the SIGTERM, so do not
    wait for workers that ignore the SIGTERM, e.g. because a test set its own
    handler, and leave the time to pytest to write its reports.
    """
    paths = sorted(directory.glob("*-gw*.txt"))

    # The workers dump their stacks themselves if they got the SIGTERM too.
    _wait_for(paths, _DUMP_TIMEOUT / 2)
    asked = [p for p in paths if _size(p) == 0 and _signal(p, signal.SIGUSR1)]
    _wait_for(asked, _DUMP_TIMEOUT / 2)
    # Let the workers finish writing.
    time.sleep(0.1)

    for path in paths:
        try:
            text = path.read_text()
        except FileNotFoundError:
            continue
        if not text:
            continue
        _, worker_id = _pid_and_worker(path)
        print(f"\nStacks of the pytest-xdist worker {worker_id}:", file=out)
        out.write(text)
    out.flush()

    for path in paths:
        # A worker without its file has stopped, and its PID may be reused.
        if path.exists():
            _signal(path, signal.SIGKILL)
