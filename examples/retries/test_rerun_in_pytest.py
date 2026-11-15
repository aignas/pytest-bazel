_RUNS = []


def test_fails_the_first_time():
    _RUNS.append(1)
    assert len(_RUNS) > 1, "fails the first time only"


def test_passes():
    pass


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
