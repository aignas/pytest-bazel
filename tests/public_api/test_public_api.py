"""The public API is what the `pytest_bazel` package exports."""

import inspect

import pytest_bazel


def test_public_api():
    assert pytest_bazel.__all__ == ["main"]


def test_main_is_the_function():
    """Not a module, which `import pytest_bazel.main` gave before."""
    assert inspect.isfunction(pytest_bazel.main)
    assert pytest_bazel.main.__module__ == "pytest_bazel"


def test_no_other_public_modules():
    public = [
        name
        for name, value in vars(pytest_bazel).items()
        if inspect.ismodule(value) and not name.startswith("_") and name != "sys"
    ]

    assert public == []


if __name__ == "__main__":
    pytest_bazel.main()
