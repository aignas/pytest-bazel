def test_always_fails():
    assert "flaky" == "stable"


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
