"""Run with TESTBRIDGE_TEST_ONLY set, see BUILD.bazel."""

import pytest


class TestCase:
    def test_selected(self):
        pass

    def test_other(self):
        pytest.fail("must be deselected by the filter")


def test_selected_too():
    pytest.fail("must be deselected by the filter")


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
