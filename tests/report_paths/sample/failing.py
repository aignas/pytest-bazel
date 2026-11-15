"""Failing tests whose report the test in ../test_report_paths.py checks.

The file is not named test_*.py, so that only that test collects it.
"""

import pytest

from tests.report_paths.helper.helper import check, warn


def test_assert():
    assert 1 == 2  # noqa: PLR0133


def test_in_helper():
    check(1)


@pytest.fixture
def broken():
    raise RuntimeError("broken fixture")


def test_fixture_error(broken):
    pass


def test_warning():
    warn()
