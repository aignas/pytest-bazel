"""Warnings are written to TEST_WARNINGS_OUTPUT_FILE."""

import warnings

from pytest_bazel.warning_paths import _warnings_to_file


def test_writes_warnings_to_the_file(tmp_path):
    out = tmp_path / "warnings.txt"
    original = warnings.showwarning

    with _warnings_to_file(out):
        warnings.showwarning("hello", UserWarning, "mod.py", 3)

    assert warnings.showwarning is original
    assert out.read_text() == "mod.py:3: UserWarning: hello\n"


def test_does_nothing_without_a_file():
    original = warnings.showwarning

    with _warnings_to_file(None):
        assert warnings.showwarning is original


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
