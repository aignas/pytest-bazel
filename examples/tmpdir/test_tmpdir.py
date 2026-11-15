import os
import tempfile


def test_tmp(tmp_path):
    print("tmp_path:          ", tmp_path)
    print("TEST_TMPDIR:       ", os.environ["TEST_TMPDIR"])
    print("TMPDIR:            ", os.environ["TMPDIR"])
    print("tempfile.mkdtemp():", tempfile.mkdtemp())


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
