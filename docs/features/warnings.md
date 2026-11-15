# Paths in warnings

Under `bazel test`, the paths in pytest's warnings summary and in
`TEST_WARNINGS_OUTPUT_FILE` are relative to the runfiles root, which for the
main repository is the same as the workspace root. Python would print the
absolute path into the bazel sandbox, which is gone after the test, so an
editor could not open it. With `bazel run` or without bazel, the paths stay
absolute.

<!-- source: examples/warnings/helper.py -->
```{code-block} python
:caption: examples/warnings/helper.py

import warnings


def old_api():
    warnings.warn("old_api() is deprecated", DeprecationWarning, stacklevel=1)
```
<!-- end -->

<!-- run: warnings -->
```console
$ bazel test //examples/warnings:warnings_test
//examples/warnings:warnings_test PASSED in <time>
$ cat bazel-testlogs/examples/warnings/warnings_test/test.log
=============================== warnings summary ===============================
examples/warnings/test_warnings.py::test_uses_old_api
  examples/warnings/helper.py:5: DeprecationWarning: old_api() is deprecated
    warnings.warn("old_api() is deprecated", DeprecationWarning, stacklevel=1)
- generated xml file: bazel-testlogs/examples/warnings/warnings_test/test.xml -
```
<!-- end -->
