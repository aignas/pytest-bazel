import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from pytest_bazel._impl.env import BazelEnv
from pytest_bazel._impl.sigterm import _interrupt_on_sigterm

pytestmark = pytest.mark.skipif(os.name != "posix", reason="posix only")

# A test that hangs in the main thread while another thread waits too.
_HANGING_TEST = """
import threading, time
from pathlib import Path

def test_fast():
    pass

def test_hangs():
    threading.Thread(target=time.sleep, args=(60,), name="helper", daemon=True).start()
    Path("started").touch()
    time.sleep(60)
"""


def test_handler_is_restored():
    previous = signal.getsignal(signal.SIGTERM)

    with _interrupt_on_sigterm(BazelEnv({"BAZEL_TEST": "1"})):
        assert signal.getsignal(signal.SIGTERM) is not previous

    assert signal.getsignal(signal.SIGTERM) is previous


def test_not_installed_outside_of_bazel_test():
    previous = signal.getsignal(signal.SIGTERM)

    with _interrupt_on_sigterm(BazelEnv({})):
        assert signal.getsignal(signal.SIGTERM) is previous


def test_sigterm_raises_keyboard_interrupt():
    env = BazelEnv({"BAZEL_TEST": "1", "TEST_TIMEOUT": "5"})

    def wait_for_sigterm():
        os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(5)

    with _interrupt_on_sigterm(env), pytest.raises(KeyboardInterrupt):
        wait_for_sigterm()


def _bazel_env(tmp_path):
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("TEST_", "XML_", "TESTBRIDGE_"))
    }
    env.update(
        BAZEL_TEST="1",
        PYTHONPATH=os.pathsep.join(sys.path),
        TEST_TIMEOUT="60",
        XML_OUTPUT_FILE=str(tmp_path / "test.xml"),
    )
    return env


def test_timeout_prints_stacks_and_writes_reports(tmp_path):
    (tmp_path / "test_hang.py").write_text(_HANGING_TEST)
    proc = subprocess.Popen(
        [sys.executable, "-m", "pytest_bazel", "-p", "no:randomly", "test_hang.py"],
        cwd=tmp_path,
        env=_bazel_env(tmp_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 30
    while not (tmp_path / "started").exists():
        assert time.monotonic() < deadline, "the test did not start"
        time.sleep(0.1)

    proc.send_signal(signal.SIGTERM)
    stdout, stderr = proc.communicate(timeout=30)

    assert proc.returncode == pytest.ExitCode.INTERRUPTED, stdout + stderr
    assert "SIGTERM after the timeout of 60s" in stderr
    assert "helper" in stderr or "Thread 0x" in stderr, stderr
    # The stacks show where the test hangs.
    assert "in test_hangs" in stderr, stderr
    assert "KeyboardInterrupt" in stdout
    xml = Path(tmp_path / "test.xml").read_text()
    assert 'name="test_fast"' in xml, xml


if __name__ == "__main__":
    from pytest_bazel import main

    main()
