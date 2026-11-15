# JUnit XML reports

`pytest_bazel` writes the JUnit XML report to the file bazel asks for, which
bazel shows in `bazel-testlogs` and in the build event protocol. The test
suite is named after the target, so that reports of many targets can be told
apart.

<!-- source: examples/junit_xml/test_junit_xml.py -->
```{code-block} python
:caption: examples/junit_xml/test_junit_xml.py

def test_ok():
    pass


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- run: junit_xml -->
```console
$ bazel test //examples/junit_xml:junit_xml_test
//examples/junit_xml:junit_xml_test PASSED in <time>
$ cat bazel-testlogs/examples/junit_xml/junit_xml_test/test.xml
<testsuites name="pytest tests">
  <testsuite name="//examples/junit_xml:junit_xml_test" errors="0" failures="0" skipped="0" tests="1" time="<time>" timestamp="<timestamp>" hostname="<hostname>">
    <testcase classname="examples.junit_xml.test_junit_xml" name="test_ok" time="<time>" />
  </testsuite>
</testsuites>
```
<!-- end -->
