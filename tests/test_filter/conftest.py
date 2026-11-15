"""Fail if the filter selects nothing, which pytest_bazel would let pass."""

import pytest


def pytest_collection_finish(session: pytest.Session) -> None:
    if not session.items:
        msg = "TESTBRIDGE_TEST_ONLY selected no tests"
        raise pytest.UsageError(msg)
