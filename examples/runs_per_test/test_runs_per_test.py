import random


def test_random():
    print("random number:", random.randint(0, 100))


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
