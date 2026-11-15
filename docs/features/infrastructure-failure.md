# Telling a broken setup from failing tests

When pytest cannot run the tests at all, e.g. because of an unknown flag, a
missing plugin or a broken `conftest.py`, `pytest_bazel` writes
`TEST_INFRASTRUCTURE_FAILURE_FILE`. Bazel keeps it as
`test.infrastructure_failure` and lists it in the build event protocol, so that
CI can tell such a failure from failing tests. The status of the test does not
change.

<!-- source: examples/infrastructure_failure/BUILD.bazel -->
<!-- end -->

<!-- run: infrastructure_failure -->
<!-- end -->
