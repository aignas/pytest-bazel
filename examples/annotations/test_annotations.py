import pytest


def test_passes():
    pass


def test_fails():
    assert 1 + 1 == 3


@pytest.mark.skip(reason="not today")
def test_skipped():
    pass


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
