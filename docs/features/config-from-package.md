---
# The examples that dev/update_docs runs for the `run` blocks below.
pytest_bazel_examples:
  config_from_package_default:
    target: '//examples/config_from_package:default_test'
    keep: 'passed|PASSED'
  config_from_package:
    target: '//examples/config_from_package:config_from_package_test'
    keep: 'passed|PASSED'
---

# Using the pytest config of the package

Opt-in with `PYTEST_BAZEL_CONFIG_FROM_PACKAGE=1`, this will be the default in
1.0. pytest looks for its config file in the runfiles root only, so a
`pytest.ini` next to the tests is not used. With the flag, the config file in
the package of the target, or in its parents, is used. Test ids stay
relative to the runfiles root, while `testpaths` are relative to the config
file, as when pytest runs next to it.

<!-- source: examples/config_from_package/pytest.ini -->
```{code-block} ini
:caption: examples/config_from_package/pytest.ini

[pytest]
addopts = --verbose
```
<!-- end -->

<!-- source: examples/config_from_package/BUILD.bazel -->
```{code-block} starlark
:caption: examples/config_from_package/BUILD.bazel

load("@rules_python//python:py_test.bzl", "py_test")

[
    py_test(
        name = name,
        srcs = ["test_config_from_package.py"],
        data = ["pytest.ini"],
        env = env,
        main = "test_config_from_package.py",
        tags = ["manual"],
        deps = ["//pytest_bazel"],
    )
    for name, env in {
        "default_test": {},
        "config_from_package_test": {"PYTEST_BAZEL_CONFIG_FROM_PACKAGE": "1"},
    }.items()
]
```
<!-- end -->

Without the flag, `addopts = --verbose` is not used:

<!-- run: config_from_package_default -->
```console
$ bazel test //examples/config_from_package:default_test
//examples/config_from_package:default_test PASSED in <time>
$ cat bazel-testlogs/examples/config_from_package/default_test/test.log
============================== 2 passed in <time> ===============================
```
<!-- end -->

With the flag:

<!-- run: config_from_package -->
```console
$ bazel test //examples/config_from_package:config_from_package_test
//examples/config_from_package:config_from_package_test PASSED in <time>
$ cat bazel-testlogs/examples/config_from_package/config_from_package_test/test.log
examples/config_from_package/test_config_from_package.py::test_one PASSED [ 50%]
examples/config_from_package/test_config_from_package.py::test_two PASSED [100%]
============================== 2 passed in <time> ===============================
```
<!-- end -->
