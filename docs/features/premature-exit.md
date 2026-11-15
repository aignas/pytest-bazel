---
# The examples that dev/update_docs runs for the `run` blocks below.
pytest_bazel_examples:
  premature_exit:
    target: '//examples/premature_exit:premature_exit_test'
---

# Tests that exit early

A test that ends the process with `os._exit(0)` would pass, because bazel
only sees the exit code. `pytest_bazel` creates `TEST_PREMATURE_EXIT_FILE`
before running pytest and removes it once pytest is done, so bazel fails such
a test.

<!-- source: examples/premature_exit/test_premature_exit.py -->
```{code-block} python
:caption: examples/premature_exit/test_premature_exit.py

import os


def test_exits_early():
    os._exit(0)


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- run: premature_exit -->
```console
$ bazel test //examples/premature_exit:premature_exit_test
//examples/premature_exit:premature_exit_test FAILED in <time>
$ cat bazel-testlogs/examples/premature_exit/premature_exit_test/test.log
============================= test session starts ==============================
collected 1 item

examples/premature_exit/test_premature_exit.py -- Test exited prematurely (TEST_PREMATURE_EXIT_FILE exists) --
```
<!-- end -->
