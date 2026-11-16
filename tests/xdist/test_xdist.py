"""pytest-xdist through pytest_bazel, run like bazel test runs a test."""

import importlib
import io
import os
import signal
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

import pytest

from pytest_bazel.main import BazelEnv, _plugin_args
from pytest_bazel.workers import stop_workers

pytestmark = pytest.mark.skipif(os.name != "posix", reason="posix only")

_NUM_TESTS = 8

_PARALLEL = f"""
import os, time
from pathlib import Path
import pytest

@pytest.mark.parametrize("n", range({_NUM_TESTS}))
def test_n(n):
    time.sleep(0.2)
    worker = os.environ["PYTEST_XDIST_WORKER"]
    (Path(os.environ["WORKERS_LOG"]) / f"{{worker}}-{{n}}").touch()
"""

# Each hanging worker touches a `started-<pid>` file before it hangs.
_STARTED = "Path(f'started-{os.getpid()}').touch()"

# name: (test file, workers, the stacks that must be printed)
_TIMEOUTS = {
    "one_worker": (
        f"""
import os, time
from pathlib import Path

def test_hangs():
    {_STARTED}
    time.sleep(60)
""",
        1,
        ["worker gw0:", "in test_hangs"],
    ),
    "both_workers": (
        f"""
import os, time
from pathlib import Path

def test_hangs_1():
    {_STARTED}
    time.sleep(60)

def test_hangs_2():
    {_STARTED}
    time.sleep(60)
""",
        2,
        ["worker gw0:", "worker gw1:", "in test_hangs_1", "in test_hangs_2"],
    ),
    "fixture": (
        f"""
import os, time
from pathlib import Path
import pytest

@pytest.fixture
def slow_database():
    {_STARTED}
    time.sleep(60)

def test_uses_database(slow_database):
    pass
""",
        1,
        ["worker gw0:", "in slow_database"],
    ),
    "collection": (
        f"""
import os, time
from pathlib import Path

{_STARTED}
time.sleep(60)

def test_never_runs():
    pass
""",
        2,
        ["worker gw0:", "worker gw1:", "in <module>"],
    ),
    # The worker does not stop on SIGTERM, so the main process asks it for its
    # stacks with SIGUSR1 and kills it, as bazel would only SIGKILL it later.
    "own_sigterm_handler": (
        f"""
import os, signal, time
from pathlib import Path

def test_ignores_sigterm():
    signal.signal(signal.SIGTERM, lambda *_: None)
    {_STARTED}
    time.sleep(60)
""",
        1,
        ["worker gw0:", "in test_ignores_sigterm"],
    ),
}

# Bazel sends SIGKILL 15 seconds after the SIGTERM by default, see
# --local_termination_grace_seconds. Stop well before, it takes ~2s.
_MAX_STOP_SECONDS = 5


def _env(tmp_path, **extra):
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("TEST_", "XML_", "TESTBRIDGE_", "PYTEST_XDIST"))
    }
    (tmp_path / "tmp").mkdir(exist_ok=True)
    env.update(
        BAZEL_TEST="1",
        PYTHONPATH=os.pathsep.join(sys.path),
        TEST_TMPDIR=str(tmp_path / "tmp"),
        XML_OUTPUT_FILE=str(tmp_path / "test.xml"),
        **extra,
    )
    return env


def _cmd(*args):
    return [sys.executable, "-m", "pytest_bazel", "-p", "no:randomly", *args]


def _run(tmp_path, *args, **extra):
    result = subprocess.run(
        _cmd(*args),
        cwd=tmp_path,
        env=_env(tmp_path, **extra),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr


def _passed(xml_file):
    root = ET.parse(xml_file).getroot()
    return {
        f"{c.get('classname')}.{c.get('name')}"
        for c in root.iter("testcase")
        if not list(c)
    }


def test_loaded_with_xdist(tmp_path):
    args = _plugin_args(BazelEnv({"BAZEL_TEST": "1", "TEST_TMPDIR": str(tmp_path)}))

    assert "pytest_bazel.workers" in args


def test_not_loaded_without_xdist(tmp_path, monkeypatch):
    find_spec = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name, *a: None if name == "xdist" else find_spec(name, *a),
    )

    args = _plugin_args(BazelEnv({"BAZEL_TEST": "1", "TEST_TMPDIR": str(tmp_path)}))

    assert "pytest_bazel.workers" not in args


def test_runs_in_parallel(tmp_path):
    (tmp_path / "test_parallel.py").write_text(_PARALLEL)
    log = tmp_path / "workers"
    log.mkdir()

    code, output = _run(tmp_path, "-n", "2", "test_parallel.py", WORKERS_LOG=str(log))

    assert code == pytest.ExitCode.OK, output
    assert len(_passed(tmp_path / "test.xml")) == _NUM_TESTS, output
    workers = {p.name.partition("-")[0] for p in log.iterdir()}
    assert workers == {"gw0", "gw1"}, output
    # The plugins of pytest_bazel are not imported before pytest loads them.
    assert "PytestAssertRewriteWarning" not in output, output


def test_workers_remove_their_files(tmp_path):
    (tmp_path / "test_ok.py").write_text("def test_ok(): pass\n")

    code, output = _run(tmp_path, "-n", "2", "test_ok.py")

    assert code == pytest.ExitCode.OK, output
    assert list((tmp_path / "tmp" / "pytest_bazel_workers").iterdir()) == []


def test_files_of_crashed_workers_are_removed(tmp_path):
    (tmp_path / "test_crash.py").write_text(
        "import os\ndef test_crash(): os._exit(1)\ndef test_ok(): pass\n"
    )

    code, output = _run(tmp_path, "-n", "1", "-p", "no:randomly", "test_crash.py")

    assert code == pytest.ExitCode.TESTS_FAILED, output
    assert "crashed" in output, output
    assert list((tmp_path / "tmp" / "pytest_bazel_workers").iterdir()) == [], output


def test_stop_workers_when_a_worker_stops_meanwhile(tmp_path):
    """A worker removes its file when it stops, also while it is being stopped."""
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    stacks = tmp_path / f"{proc.pid}-gw0.txt"
    stacks.write_text("")
    timer = threading.Timer(0.3, stacks.unlink)
    timer.start()
    try:
        stop_workers(tmp_path, io.StringIO())
        # It is gone from the files, so its PID may belong to another process.
        assert proc.poll() is None
    finally:
        timer.cancel()
        proc.kill()
        proc.wait()


def test_sharding_with_workers(tmp_path):
    (tmp_path / "test_parallel.py").write_text(_PARALLEL)
    log = tmp_path / "workers"
    log.mkdir()

    shards = []
    for index in range(2):
        code, output = _run(
            tmp_path,
            "-n",
            "2",
            "test_parallel.py",
            WORKERS_LOG=str(log),
            TEST_SHARD_INDEX=str(index),
            TEST_TOTAL_SHARDS="2",
            TEST_SHARD_STATUS_FILE=str(tmp_path / "shard"),
        )
        assert code == pytest.ExitCode.OK, output
        shards.append(_passed(tmp_path / "test.xml"))

    assert not shards[0] & shards[1]
    assert len(shards[0] | shards[1]) == _NUM_TESTS


def test_empty_shard_with_workers_passes(tmp_path):
    (tmp_path / "test_one.py").write_text("def test_one(): pass\n")

    codes = [
        _run(
            tmp_path,
            "-n",
            "2",
            "test_one.py",
            TEST_SHARD_INDEX=str(index),
            TEST_TOTAL_SHARDS="2",
            TEST_SHARD_STATUS_FILE=str(tmp_path / "shard"),
        )
        for index in range(2)
    ]

    assert [code for code, _ in codes] == [pytest.ExitCode.OK] * 2, codes


def test_warnings_of_workers_are_written_once(tmp_path):
    (tmp_path / "test_warns.py").write_text(
        "import warnings\n"
        "def test_warns():\n"
        "    warnings.warn('from a worker', DeprecationWarning)\n"
    )
    out = tmp_path / "test.warnings"

    code, output = _run(
        tmp_path, "-n", "2", "test_warns.py", TEST_WARNINGS_OUTPUT_FILE=str(out)
    )

    assert code == pytest.ExitCode.OK, output
    assert out.read_text().count("DeprecationWarning: from a worker") == 1, (
        out.read_text()
    )


def test_auto_warns_without_cpu_count(tmp_path):
    (tmp_path / "test_ok.py").write_text("def test_ok(): pass\n")

    code, output = _run(tmp_path, "-n", "auto", "test_ok.py")

    assert code == pytest.ExitCode.OK, output
    assert "PYTEST_XDIST_AUTO_NUM_WORKERS=N" in output


def test_auto_uses_the_cpu_count(tmp_path):
    (tmp_path / "test_ok.py").write_text("def test_ok(): pass\n")

    code, output = _run(
        tmp_path, "-n", "auto", "test_ok.py", PYTEST_XDIST_AUTO_NUM_WORKERS="2"
    )

    assert code == pytest.ExitCode.OK, output
    assert "PYTEST_XDIST_AUTO_NUM_WORKERS=N" not in output
    assert "2 workers" in output, output


@pytest.mark.parametrize(
    ("scenario", "process_group"),
    [
        *((name, True) for name in _TIMEOUTS),
        # Bazel usually signals the process group, but not always.
        ("one_worker", False),
    ],
    ids=lambda v: v if isinstance(v, str) else ("group" if v else "main_only"),
)
def test_timeout(tmp_path, scenario, process_group):
    source, workers, want = _TIMEOUTS[scenario]
    (tmp_path / "test_hang.py").write_text(source)
    proc = subprocess.Popen(
        _cmd("-n", str(workers), "test_hang.py"),
        cwd=tmp_path,
        env=_env(tmp_path, TEST_TIMEOUT="60"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    deadline = time.monotonic() + 30
    while len(list(tmp_path.glob("started-*"))) < workers:
        assert time.monotonic() < deadline, "the workers did not start"
        time.sleep(0.1)

    if process_group:
        os.killpg(proc.pid, signal.SIGTERM)
    else:
        proc.send_signal(signal.SIGTERM)
    terminated = time.monotonic()
    stdout, stderr = proc.communicate(timeout=30)
    stopped_after = time.monotonic() - terminated

    for line in want:
        assert line in stderr, stdout + stderr
    # pytest still writes its reports, well before bazel kills the test.
    assert (tmp_path / "test.xml").exists(), stdout + stderr
    assert stopped_after < _MAX_STOP_SECONDS, stopped_after


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
