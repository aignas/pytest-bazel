---
# The examples that dev/update_docs runs for the `run` blocks below.
pytest_bazel_examples:
  config_from_package_off:
    target: '//examples/config_from_package:off_test'
    keep: 'passed|PASSED'
  config_from_package:
    target: '//examples/config_from_package:config_from_package_test'
    keep: 'passed|PASSED'
---

# Using the pytest config of the package

On by default since 1.0, set `PYTEST_BAZEL_CONFIG_FROM_PACKAGE=0` to turn it
off. pytest looks for its config file in the runfiles root only, so a
`pytest.ini` next to the tests is not used. With it, the config file in the
package of the target, or in its parents, is used. The `conftest.py` files above
the config file, e.g. in the workspace root, are still loaded.

pytest runs in the runfiles root, so the test ids and the paths in the options
of the config file, e.g. `--ignore` or `--deselect` in `addopts`, are relative
to it, as in the workspace root. Only `testpaths` and `pythonpath` are relative
to the config file, as when pytest runs next to it:

```ini
# pkg/pytest.ini
[pytest]
# pkg/tests
testpaths = tests
# pkg/tests/slow, relative to the runfiles root
addopts = --ignore=pkg/tests/slow
```

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
        "off_test": {"PYTEST_BAZEL_CONFIG_FROM_PACKAGE": "0"},
        "config_from_package_test": {},
    }.items()
]
```
<!-- end -->

With `PYTEST_BAZEL_CONFIG_FROM_PACKAGE=0`, `addopts = --verbose` is not used:

<!-- run: config_from_package_off -->
```console
$ bazel test //examples/config_from_package:off_test
//examples/config_from_package:off_test PASSED in <time>
$ cat bazel-testlogs/examples/config_from_package/off_test/test.log
============================== 2 passed in <time> ===============================
```
<!-- end -->

By default:

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
