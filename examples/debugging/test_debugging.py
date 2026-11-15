def test_add():
    total = 1 + 1
    breakpoint()
    assert total == 3


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
