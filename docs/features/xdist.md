---
# The examples that dev/update_docs runs for the `run` blocks below.
pytest_bazel_examples:
  xdist:
    target: '//examples/xdist:xdist_test'
    keep: 'workers \[|passed'
  xdist_timeout:
    target: '//examples/xdist:xdist_hangs_test'
    flags: ['--test_timeout=10']
    keep: 'SIGTERM|Stacks of the pytest-xdist|test_xdist_hangs.py.* in '
---

# Running tests in parallel with pytest-xdist

[pytest-xdist] runs the tests of a target in several worker processes. Bazel
reserves 1 CPU for a test, so reserve more with the `cpu:N` tag and tell
`-n auto` about them with `PYTEST_XDIST_AUTO_NUM_WORKERS`. Bazel does not pass
the number of reserved CPUs to the test, so without it `-n auto` starts a
worker for every CPU of the machine, and `pytest_bazel` warns about that.

<!-- source: examples/xdist/BUILD.bazel -->
```{code-block} starlark
:caption: examples/xdist/BUILD.bazel

load("@rules_python//python:py_test.bzl", "py_test")

py_test(
    name = "xdist_test",
    srcs = ["test_xdist.py"],
    # Start a worker for every CPU that bazel reserved for the test.
    args = ["--numprocesses=auto"],
    env = {"PYTEST_XDIST_AUTO_NUM_WORKERS": "2"},
    main = "test_xdist.py",
    tags = [
        "cpu:2",
        "manual",
    ],
    deps = [
        "//pytest_bazel",
        "@pypi//pytest_xdist",
    ],
)

py_test(
    name = "xdist_hangs_test",
    srcs = ["test_xdist_hangs.py"],
    args = ["--numprocesses=1"],
    main = "test_xdist_hangs.py",
    tags = [
        "cpu:2",
        "manual",
    ],
    deps = [
        "//pytest_bazel",
        "@pypi//pytest_xdist",
    ],
)
```
<!-- end -->

<!-- run: xdist -->
```console
$ bazel test //examples/xdist:xdist_test
//examples/xdist:xdist_test PASSED in <time>
$ cat bazel-testlogs/examples/xdist/xdist_test/test.log
2 workers [4 items]
============================== 4 passed in <time> ===============================
```
<!-- end -->

Sharding, `--test_filter`, the JUnit XML and the annotations work with the
workers too. When bazel times out the test, the stacks of the workers are
printed as well, as the tests run there. That works for tests, fixtures and
collection that hang, and for workers that ignore the SIGTERM. The workers are
stopped then, so that pytest writes its reports before bazel kills the test:

<!-- run: xdist_timeout -->
```console
$ bazel test //examples/xdist:xdist_hangs_test --test_timeout=10
//examples/xdist:xdist_hangs_test TIMEOUT in <time>
$ cat bazel-testlogs/examples/xdist/xdist_hangs_test/test.log
bazel stopped the test with SIGTERM after the timeout of 10s. Stacks of all threads:
  File "<runfiles>/_main/examples/xdist/test_xdist_hangs.py", line 15 in <module>
Stacks of the pytest-xdist worker gw0:
  File "<runfiles>/_main/examples/xdist/test_xdist_hangs.py", line 9 in test_hangs
```
<!-- end -->

[pytest-xdist]: https://pypi.org/project/pytest-xdist/
