---
# The examples that dev/update_docs runs for the `run` blocks below.
pytest_bazel_examples:
  junit_output:
    target: '//examples/junit_output:junit_output_test'
    files: ['test.xml']
---

# The output of failed tests in the JUnit XML

Opt-in with `PYTEST_BAZEL_JUNIT_OUTPUT=1`, this will be the default in 1.0.
CI systems and the build event protocol show the JUnit XML of a test, but
pytest only adds the output of the tests to it with `junit_logging`, so a
failure shows up without what the test printed or logged. With the flag, the
captured stdout, stderr and log records of failed tests are in the XML.
Passing tests are left out to keep it small, pass
`-o junit_log_passing_tests=true` to add them.

<!-- source: examples/junit_output/test_junit_output.py -->
```{code-block} python
:caption: examples/junit_output/test_junit_output.py

import logging


def test_passes():
    print("not in the XML, the test passes")


def test_fails():
    print("connecting to the database")
    logging.getLogger(__name__).warning("retrying after a timeout")
    assert "connected" == "timed out"


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- source: examples/junit_output/BUILD.bazel -->
```{code-block} starlark
:caption: examples/junit_output/BUILD.bazel

load("@rules_python//python:py_test.bzl", "py_test")

py_test(
    name = "junit_output_test",
    srcs = ["test_junit_output.py"],
    env = {"PYTEST_BAZEL_JUNIT_OUTPUT": "1"},
    main = "test_junit_output.py",
    tags = ["manual"],
    deps = ["//pytest_bazel"],
)
```
<!-- end -->

<!-- run: junit_output -->
```console
$ bazel test //examples/junit_output:junit_output_test
//examples/junit_output:junit_output_test FAILED in <time>
$ cat bazel-testlogs/examples/junit_output/junit_output_test/test.xml
<testsuites name="pytest tests">
  <testsuite name="//examples/junit_output:junit_output_test" errors="0" failures="1" skipped="0" tests="2" time="<time>" timestamp="<timestamp>" hostname="<hostname>">
    <testcase classname="examples.junit_output.test_junit_output" name="test_passes" time="<time>" />
    <testcase classname="examples.junit_output.test_junit_output" name="test_fails" time="<time>">
      <failure message="AssertionError: assert 'connected' == 'timed out'&#10;  &#10;  - timed out&#10;  + connected">def test_fails():
        print("connecting to the database")
        logging.getLogger(__name__).warning("retrying after a timeout")
&gt;       assert "connected" == "timed out"
E       AssertionError: assert 'connected' == 'timed out'
E
E         - timed out
E         + connected

examples/junit_output/test_junit_output.py:11: AssertionError</failure>
      <system-out>--------------------------------- Captured Log ---------------------------------
WARNING  test_junit_output:test_junit_output.py:10 retrying after a timeout
--------------------------------- Captured Out ---------------------------------
connecting to the database

</system-out>
      <system-err>--------------------------------- Captured Err ---------------------------------

</system-err>
    </testcase>
  </testsuite>
</testsuites>
```
<!-- end -->
