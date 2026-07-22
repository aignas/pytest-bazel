"""A macro to be used to easily integrate pytest into your bazel setup."""

load("@rules_python//python:py_test.bzl", "py_test")

_PYTEST_BAZEL_TARGET = Label("//pytest_bazel")
_PYTEST_BAZEL_PKG = Label("@pypi//pytest_bazel")

def pytest_test(*, deps = [], internal = False, **kwargs):
    """Use pytest-bazel for running pytest tests

    Args:
        deps: Deps to pass to the test.
        internal: {type}`bool` If this is used in internal tests, where
            pytest_bazel dependency should not be added.
        **kwargs: Extra args passed to the py_test.
    """
    deps = [
        _PYTEST_BAZEL_TARGET if internal else _PYTEST_BAZEL_PKG
    ] + deps

    # pass the sources directly
    args = [
        "$(location :%s)" % x for x in srcs
    ] if internal else []
    args += kwargs.pop("args", [])

    if kwargs.get("shard_count"):
        deps.append("@pypi//pytest_shard")

    py_test(
        deps = deps,
        main_module = "pytest_bazel",
        args = args,
        **kwargs
    )
