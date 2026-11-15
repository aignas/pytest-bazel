def test_first():
    assert 1 + 1 == 3


def test_second():
    assert "a" == "b"


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
