# Telling a broken setup from failing tests

When pytest cannot run the tests at all, e.g. because of an unknown flag, a
missing plugin or a broken `conftest.py`, `pytest_bazel` writes
`TEST_INFRASTRUCTURE_FAILURE_FILE`. Bazel keeps it as
`test.infrastructure_failure` and lists it in the build event protocol, so that
CI can tell such a failure from failing tests. The status of the test does not
change.

<!-- source: examples/infrastructure_failure/BUILD.bazel -->
```{code-block} starlark
:caption: examples/infrastructure_failure/BUILD.bazel

load("@rules_python//python:py_test.bzl", "py_test")

py_test(
    name = "infrastructure_failure_test",
    srcs = ["test_infrastructure_failure.py"],
    # A typo in the args.
    args = ["--verbos"],
    main = "test_infrastructure_failure.py",
    tags = ["manual"],
    deps = ["//pytest_bazel"],
)
```
<!-- end -->

<!-- run: infrastructure_failure -->
```console
$ bazel test //examples/infrastructure_failure:infrastructure_failure_test
//examples/infrastructure_failure:infrastructure_failure_test FAILED in <time>
$ cat bazel-testlogs/examples/infrastructure_failure/infrastructure_failure_test/test.log
pytest.main(): error: unrecognized arguments: --verbos
$ cat bazel-testlogs/examples/infrastructure_failure/infrastructure_failure_test/test.infrastructure_failure
pytest could not run the tests (USAGE_ERROR), e.g. because of an unknown flag or a missing plugin. See the test log for details.
```
<!-- end -->
