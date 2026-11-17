---
# The examples that dev/update_docs runs for the `run` blocks below.
pytest_bazel_examples:
  fail_fast:
    target: '//examples/fail_fast:fail_fast_test'
    flags: ['--test_runner_fail_fast']
---

# Stopping at the first failure with `--test_runner_fail_fast`

`bazel test --test_runner_fail_fast` passes `--exitfirst` to pytest.

<!-- source: examples/fail_fast/test_fail_fast.py -->
```{code-block} python
:caption: examples/fail_fast/test_fail_fast.py

def test_first():
    assert 1 + 1 == 3


def test_second():
    assert "a" == "b"


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- run: fail_fast -->
```console
$ bazel test //examples/fail_fast:fail_fast_test --test_runner_fail_fast
//examples/fail_fast:fail_fast_test FAILED in <time>
$ cat bazel-testlogs/examples/fail_fast/fail_fast_test/test.log
============================= test session starts ==============================
testpaths: examples/fail_fast
collected 2 items

examples/fail_fast/test_fail_fast.py F

=================================== FAILURES ===================================
__________________________________ test_first __________________________________

    def test_first():
>       assert 1 + 1 == 3
E       assert (1 + 1) == 3

examples/fail_fast/test_fail_fast.py:2: AssertionError
- generated xml file: bazel-testlogs/examples/fail_fast/fail_fast_test/test.xml -
=========================== short test summary info ============================
FAILED examples/fail_fast/test_fail_fast.py::test_first - assert (1 + 1) == 3
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
============================== 1 failed in <time> ===============================
Pytest exit code: ExitCode.TESTS_FAILED
```
<!-- end -->
