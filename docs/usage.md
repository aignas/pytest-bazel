# Usage

Install this by including it into your `requirements.in` or `pyproject.toml` file:
```
pytest-bazel[all]
```

And then you can use it as follows:

## With `pytest_test` from `rules_python`

Since `rules_python` 2.5.0, the `pytest_test` macro creates a `py_test`
that runs its `srcs` through `pytest_bazel`, so no entrypoint is needed:

```starlark
load("@rules_python//python:pytest_test.bzl", "pytest_test")

pytest_test(
    name = "my_test",
    srcs = ["my_test.py"],
)
```

See the [rules_python docs][pytest_test] for the other arguments, e.g.
`python_versions` to run the tests with several Python versions.

[pytest_test]: https://rules-python.readthedocs.io/en/latest/api/rules_python/python/pytest_test.html

## As a python entrypoint

Using it as an alternative to `unittest.main()` in a `py_test` rule.

```python
import pytest_bazel

...

if __name__ == "__main__":
    pytest_bazel.main()
```

```starlark
# BUILD.bazel contents
load("@rules_python//python:py_test.bzl", "py_test")

py_test(
    name = "my_test",
    # ...
    deps = ["@pypi//pytest_bazel"],
)
```

## As a macro

Using it to create a macro, this shows how to create a replacement for the
`rules_python_pytest` `py_pytest_test` macro. The benefit is that this defines
all of the necessary files in a single place.

```starlark
# pytest_test.bzl contents
load("@rules_python//python:py_library.bzl", "py_library")
load("@rules_python//python:py_test.bzl", "py_test")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")

def pytest_test(name, srcs, **kwargs):
    # this is only needed for passing srcs
    deps = kwargs.pop("deps", [])
    data = kwargs.pop("data", [])
    env = kwargs.pop("env", {})
    py_library(
        name = name + ".lib",
        srcs = srcs,
        deps = deps,
        data = data,
        testonly = True,
        **kwargs,
    )

    py_console_script_binary(
        name = name,
        pkg = "@pypi//pytest_bazel",  # assuming your hub repo name is `pypi`.
        script = "pytest_bazel",
        binary_rule = py_test,
        deps = [
            # The test sources are here
            name + ".lib",
            # Add extra test deps below, e.g. for sharding support, etc.
        ],
        data = data + srcs,
        env = env,
        testonly = True,
        # The following is reusing the ideas defined in
        # https://github.com/caseyduquettesc/rules_python_pytest/blob/main/python_pytest/defs.bzl
        args = kwargs.get("args", []) + [
            # Passing of srcs is optional and this is only to show how one
            # would reimplement what `rules_python_pytest` has done.
            "$(location :%s)" % x for x in srcs
        ],
        **kwargs,
    )

# BUILD.bazel contents
load("//:pytest_test.bzl", "pytest_test")

pytest_test(
    name = "my_test",
    # ...
    deps = ["@pypi//pytest_bazel"],
)
```

## Namespace packages

With `PYTEST_BAZEL_CONSIDER_NAMESPACE_PACKAGES=1`, `pytest_bazel` passes
`-o consider_namespace_packages=true` on pytest 8.1+. This will be the default
in 1.0.

Bazel packages usually have no `__init__.py`, so without it pytest names
`foo/numpy/test_bar.py` (with `foo/numpy/__init__.py`) `numpy.test_bar`, and
the first-party `foo/numpy` then shadows the real `numpy` for the code under
test. With it, the module is named `foo.numpy.test_bar`.

Passing `-o consider_namespace_packages=false` in `args` turns it off again.

## Public API

`pytest_bazel.main()`, `python -m pytest_bazel` and the `pytest_bazel` console
script are the public API, and the `PYTEST_BAZEL_*` env vars configure it. The
rest, e.g. the modules in `pytest_bazel._impl` and the `--bazel-*` options of
its pytest plugins, is private and may change in any release.
