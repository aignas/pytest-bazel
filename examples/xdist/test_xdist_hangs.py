import time


def test_fast():
    pass


def test_hangs():
    time.sleep(60)


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
