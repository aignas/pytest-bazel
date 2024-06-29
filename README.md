# pytest-bazel

A pytest wrapper for supporting bazel's rule_python. This is supposed to be
used via PyPI and no bazel rules will be exported for the time being.

## Goals

- [ ] Looking at the [test_encyclopedia], the following can be still added:
    - [ ] `--capture=no` depending on whether `bazel run` or `bazel test` is used.
    - [ ] `TEST_WARNINGS_OUTPUT_FILE` is used to output `warnings.warn` usage.
    - [ ] `TEST_TMPDIR` is used
    - [ ] `TEST_SRCDIR` is maybe used to pass in the root where to start discovery.
    - [ ] `TEST_RANDOM_SEED` is used for predictive tests.
    - [ ] `TEST_INFRASTRUCTURE_FAILURE_FILE` is used when `pytest` fails to discover any tests.
- [ ] Consider recommendations on project structure (separate `tests` dir may
  facilitate integration with `pytest`, but this needs further checking).
- [ ] rules_python FR are submitted.
- [ ] No passing of files as args is needed. Pytest discovery is working as expected.

[test_encyclopedia]: https://bazel.build/reference/test-encyclopedia

## Usage

**NOTE, this is not fully tested and is in a very early POC state!**

### Pattern 1

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

### Pattern 2

Using it to create a macro, this shows how to create a replacement for the
`rules_python_pytest` `py_pytest_test` macro. The benefit is that this defines
all of the necessary files in a single place.

```starlark
# pytest_test.bzl contents
load("@rules_python//python:py_test.bzl", "py_test")
load("@rules_python//python:py_library.bzl", "py_library")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")

def pytest_test(name, visibility = None, **kwargs):
    # this is only needed for passing srcs
    py_library(
        name = name + ".lib",
        #testonly = True,
        **kwargs,
    )

    py_console_script_binary(
        name = "test_simple",
        pkg = "@pypi//pytest_bazel",  # assuming your hub repo name is `pypi`.
        binary_rule = py_test,
        deps = [
            # The test sources are here
            name + ".lib",
            # Add extra test deps below, e.g. for sharding support, etc.
        ],
        # TODO @aignas 2024-06-29: support testonly here
        #testonly = True,
        # The following is reusing the ideas defined in
        # https://github.com/caseyduquettesc/rules_python_pytest/blob/main/python_pytest/defs.bzl
        args = kwargs.get("args", []) + [
            "$(location :%s)" % x for x in srcs],
        ],
    )

# BUILD.bazel contents
load("//:pytest_test.bzl", "pytest_test")

pytest_test(
    name = "my_test",
    # ...
    deps = ["@pypi//pytest_bazel"],
)
```

## Changelog

See [changelog].

[changelog]: ./CHANGELOG.md

## Contributing

This is right now too early to be contributed to code-wise, but issues welcome
describing what you would like to have in this project.

## Thanks

Special thanks to [rules_python_pytest] and [rules_py] projects that had some
great ideas how to integrate with `pytest`. This attempts to [unify] all of the
approaches.

[rules_python_pytest]: https://github.com/caseyduquettesc/rules_python_pytest 
[rules_py]: https://github.com/aspect-build/rules_py/blob/main/py/private/pytest.py.tmpl
[unify]: https://xkcd.com/927/
