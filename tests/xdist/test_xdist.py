"""pytest-xdist through pytest_bazel, run like bazel test runs a test."""

import importlib
import os
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import pytest

from pytest_bazel.main import BazelEnv, _plugin_args

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

_HANGING = """
import time
from pathlib import Path

def test_hangs():
    Path("started").touch()
    time.sleep(60)
"""


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


@pytest.mark.parametrize("process_group", [True, False], ids=["group", "main_only"])
def test_timeout_prints_worker_stacks(tmp_path, process_group):
    """Bazel usually sends SIGTERM to the process group, but not always."""
    (tmp_path / "test_hang.py").write_text(_HANGING)
    proc = subprocess.Popen(
        _cmd("-n", "1", "test_hang.py"),
        cwd=tmp_path,
        env=_env(tmp_path, TEST_TIMEOUT="60"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    deadline = time.monotonic() + 30
    while not (tmp_path / "started").exists():
        assert time.monotonic() < deadline, "the test did not start"
        time.sleep(0.1)

    if process_group:
        os.killpg(proc.pid, signal.SIGTERM)
    else:
        proc.send_signal(signal.SIGTERM)
    stdout, stderr = proc.communicate(timeout=30)

    assert "Stacks of the pytest-xdist worker gw0:" in stderr, stdout + stderr
    assert "in test_hangs" in stderr, stderr


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
