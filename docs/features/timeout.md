# Debugging timeouts

When a test runs out of time, bazel sends it `SIGTERM`. `pytest_bazel` then
prints the stacks of all threads, so you can see where the tests hang, and
interrupts pytest, so that it still writes its summary and the JUnit XML.

<!-- source: examples/timeout/test_timeout.py -->
```{code-block} python
:caption: examples/timeout/test_timeout.py

import time


def test_fast():
    pass


def test_hangs():
    time.sleep(60)


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- run: timeout -->
```console
$ bazel test //examples/timeout:timeout_test --test_timeout=3
//examples/timeout:timeout_test TIMEOUT in <time>
$ cat bazel-testlogs/examples/timeout/timeout_test/test.log
examples/timeout/test_timeout.py .-- Test timed out at <date> UTC --
bazel stopped the test with SIGTERM after the timeout of 3s. Stacks of all threads:
  File "<runfiles>/_main/examples/timeout/test_timeout.py", line 9 in test_hangs
  File "<runfiles>/_main/examples/timeout/test_timeout.py", line 15 in <module>
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! KeyboardInterrupt !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
============================== 1 passed in <time> ===============================
```
<!-- end -->
