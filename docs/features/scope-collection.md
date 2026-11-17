---
# The examples that dev/update_docs runs for the `run` blocks below.
pytest_bazel_examples:
  scope_collection_off:
    target: '//examples/scope_collection:off_test'
    flags: ['--test_arg=-v']
    keep: 'PASSED|FAILED'
  scope_collection:
    target: '//examples/scope_collection:scoped_test'
    flags: ['--test_arg=-v']
    keep: 'PASSED|FAILED'
---

# Only collecting the tests of the target

On by default since 1.0, set `PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE=0` to
turn it off. Without paths in the args pytest collects all tests in the
runfiles, including the tests of other packages that are there through `deps` or
`data`. With it, only the tests in the package of the target are collected. A
`testpaths` in a pytest config file in the package wins, one in a config file
shared by many packages, e.g. in the workspace root, does not. The `testpaths`
of the config file of the package, see `PYTEST_BAZEL_CONFIG_FROM_PACKAGE`, are
relative to it, e.g. `testpaths = tests` collects `<package>/tests`.

<!-- source: examples/scope_collection/BUILD.bazel -->
```{code-block} starlark
:caption: examples/scope_collection/BUILD.bazel

load("@rules_python//python:py_library.bzl", "py_library")
load("@rules_python//python:py_test.bzl", "py_test")

py_library(
    name = "own",
    testonly = True,
    srcs = ["test_own.py"],
)

[
    py_test(
        name = name,
        env = env,
        main_module = "pytest_bazel",
        tags = ["manual"],
        deps = [
            ":own",
            "//examples/scope_collection/dep",
            "//pytest_bazel",
        ],
    )
    for name, env in {
        "off_test": {"PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE": "0"},
        "scoped_test": {},
    }.items()
]
```
<!-- end -->

With `PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE=0`, the test of
`//examples/scope_collection/dep` runs too:

<!-- run: scope_collection_off -->
```console
$ bazel test //examples/scope_collection:off_test --test_arg=-v
//examples/scope_collection:off_test PASSED in <time>
$ cat bazel-testlogs/examples/scope_collection/off_test/test.log
examples/scope_collection/dep/test_dep.py::test_from_another_package PASSED [ 50%]
examples/scope_collection/test_own.py::test_own PASSED                   [100%]
```
<!-- end -->

By default:

<!-- run: scope_collection -->
```console
$ bazel test //examples/scope_collection:scoped_test --test_arg=-v
//examples/scope_collection:scoped_test PASSED in <time>
$ cat bazel-testlogs/examples/scope_collection/scoped_test/test.log
examples/scope_collection/dep/test_dep.py::test_from_another_package PASSED [ 50%]
examples/scope_collection/test_own.py::test_own PASSED                   [100%]
```
<!-- end -->
