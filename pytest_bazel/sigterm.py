"""Print where the tests were when bazel stops them on timeout."""

import contextlib
import faulthandler
import os
import signal
import sys
import threading
from collections.abc import Iterator

from pytest_bazel.env import BazelEnv, _workers_dir


@contextlib.contextmanager
def _interrupt_on_sigterm(env: BazelEnv) -> Iterator[None]:
    """Turn the SIGTERM that bazel sends on timeout into a KeyboardInterrupt.

    pytest then prints where the tests were interrupted and writes its
    reports, e.g. the JUnit XML, before bazel kills the process. The stacks of
    all threads are printed too, in case the test hangs in another thread.
    """
    if (
        not env.is_test
        or os.name != "posix"
        or threading.current_thread() is not threading.main_thread()
    ):
        yield
        return

    # pytest redirects the stderr file descriptor while tests run, so keep a
    # copy of it to print to.
    stderr = os.fdopen(os.dup(sys.stderr.fileno()), "w")

    def handler(_signum, _frame):
        # Report the KeyboardInterrupt where the tests were, not here.
        __tracebackhide__ = True
        timeout = (
            f" after the timeout of {env.test_timeout}s" if env.test_timeout else ""
        )
        print(
            f"\nbazel stopped the test with SIGTERM{timeout}. Stacks of all threads:",
            file=stderr,
            flush=True,
        )
        faulthandler.dump_traceback(file=stderr, all_threads=True)
        workers_dir = _workers_dir(env)
        if workers_dir and workers_dir.is_dir():
            # Not at the top: pytest loads the module as a plugin and warns
            # that it cannot rewrite its asserts if it was imported before.
            from pytest_bazel.workers import stop_workers  # noqa: PLC0415

            stop_workers(workers_dir, stderr)
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, handler)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)
        stderr.close()
