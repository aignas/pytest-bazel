import os


def test_exits_early():
    os._exit(0)


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
