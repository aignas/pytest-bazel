import pytest


@pytest.mark.parametrize("n", range(5))
def test_number(n):
    pass


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
