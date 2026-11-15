# Retrying flaky tests

There are two ways to retry a flaky test, use one of them, not both.

## Bazel: `flaky = True` or `--flaky_test_attempts`

Bazel runs the whole test again in a new process, up to 3 times with
`flaky = True`, or as often as `--flaky_test_attempts=N` says. When a later
attempt passes, bazel reports the test as `FLAKY`, so CI and the build event
protocol show that it is flaky. The logs of the earlier attempts are in
`bazel-testlogs/<target>/test_attempts/`. Use it by default.

<!-- source: examples/retries/test_flaky_in_bazel.py -->
```{code-block} python
:caption: examples/retries/test_flaky_in_bazel.py

def test_always_fails():
    assert "flaky" == "stable"


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- source: examples/retries/BUILD.bazel -->
```{code-block} starlark
:caption: examples/retries/BUILD.bazel

load("@rules_python//python:py_test.bzl", "py_test")

# Bazel runs the whole test again, up to 3 times.
py_test(
    name = "flaky_in_bazel_test",
    srcs = ["test_flaky_in_bazel.py"],
    flaky = True,
    main = "test_flaky_in_bazel.py",
    tags = ["manual"],
    deps = ["//pytest_bazel"],
)

# pytest-rerunfailures runs the failed tests again in the same process.
py_test(
    name = "rerun_in_pytest_test",
    srcs = ["test_rerun_in_pytest.py"],
    args = ["--reruns=2"],
    main = "test_rerun_in_pytest.py",
    tags = ["manual"],
    deps = [
        "//pytest_bazel",
        "@pypi//pytest_rerunfailures",
    ],
)
```
<!-- end -->

<!-- run: retries_bazel -->
```console
$ bazel test //examples/retries:flaky_in_bazel_test
//examples/retries:flaky_in_bazel_test FAILED in 3 out of 3 in <time>
$ cat bazel-testlogs/examples/retries/flaky_in_bazel_test/test.log
============================== 1 failed in <time> ===============================
$ find bazel-testlogs/examples/retries/flaky_in_bazel_test/test_attempts -type f
bazel-testlogs/examples/retries/flaky_in_bazel_test/test_attempts/attempt_1.log
bazel-testlogs/examples/retries/flaky_in_bazel_test/test_attempts/attempt_1.outputs_manifest/ANNOTATIONS
bazel-testlogs/examples/retries/flaky_in_bazel_test/test_attempts/attempt_1.warnings
bazel-testlogs/examples/retries/flaky_in_bazel_test/test_attempts/attempt_1.xml
bazel-testlogs/examples/retries/flaky_in_bazel_test/test_attempts/attempt_2.log
bazel-testlogs/examples/retries/flaky_in_bazel_test/test_attempts/attempt_2.outputs_manifest/ANNOTATIONS
bazel-testlogs/examples/retries/flaky_in_bazel_test/test_attempts/attempt_2.warnings
bazel-testlogs/examples/retries/flaky_in_bazel_test/test_attempts/attempt_2.xml
```
<!-- end -->

## pytest: `pytest-rerunfailures`

[pytest-rerunfailures] runs only the failed tests again, in the same process.
That is quicker for a target with many or slow tests, but bazel only sees that
the test passed, so the flakiness does not show up in bazel.

<!-- source: examples/retries/test_rerun_in_pytest.py -->
```{code-block} python
:caption: examples/retries/test_rerun_in_pytest.py

_RUNS = []


def test_fails_the_first_time():
    _RUNS.append(1)
    assert len(_RUNS) > 1, "fails the first time only"


def test_passes():
    pass


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- run: retries_pytest -->
```console
$ bazel test //examples/retries:rerun_in_pytest_test
//examples/retries:rerun_in_pytest_test PASSED in <time>
$ cat bazel-testlogs/examples/retries/rerun_in_pytest_test/test.log
examples/retries/test_rerun_in_pytest.py R..                             [100%]
- generated xml file: bazel-testlogs/examples/retries/rerun_in_pytest_test/test.xml -
========================== 2 passed, 1 rerun in <time> ==========================
```
<!-- end -->

## Both

With both, a failing test runs `attempts × (reruns + 1)` times, and every
attempt has to fit into the timeout of the test, so prefer one of them.

[pytest-rerunfailures]: https://pypi.org/project/pytest-rerunfailures/
