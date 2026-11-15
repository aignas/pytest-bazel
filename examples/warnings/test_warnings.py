from examples.warnings.helper import old_api


def test_uses_old_api():
    old_api()


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
