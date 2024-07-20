# Usage

Install this by including it into your `requirements.in` or `pyproject.toml` file:
```
pytest-bazel[all]
```

And then you can use it as follows:

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
