---
# The examples that dev/update_docs runs for the `run` blocks below.
pytest_bazel_examples:
  tmpdir:
    target: '//examples/tmpdir:tmpdir_test'
    flags: ['--test_arg=-s']
    keep: ':\s'
---

# Temporary directories

pytest's `tmp_path` and Python's `tempfile` use the private temporary
directory of the test, `TEST_TMPDIR`, which bazel cleans up. As `TEST_TMPDIR`
is usually too long for the path of an `AF_UNIX` socket, e.g. for
`multiprocessing`, `TMPDIR` points to it through a short symlink.

<!-- source: examples/tmpdir/test_tmpdir.py -->
```{code-block} python
:caption: examples/tmpdir/test_tmpdir.py

import os
import tempfile


def test_tmp(tmp_path):
    print("tmp_path:          ", tmp_path)
    print("TEST_TMPDIR:       ", os.environ["TEST_TMPDIR"])
    print("TMPDIR:            ", os.environ["TMPDIR"])
    print("tempfile.mkdtemp():", tempfile.mkdtemp())


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- run: tmpdir -->
```console
$ bazel test //examples/tmpdir:tmpdir_test --test_arg=-s
//examples/tmpdir:tmpdir_test PASSED in <time>
$ cat bazel-testlogs/examples/tmpdir/tmpdir_test/test.log
examples/tmpdir/test_tmpdir.py tmp_path:           <TEST_TMPDIR>/pytest/test_tmp0
TEST_TMPDIR:        <TEST_TMPDIR>
TMPDIR:             /tmp/pytest-bazel-<random>/tmp
tempfile.mkdtemp(): /tmp/pytest-bazel-<random>/tmp/tmp<random>
- generated xml file: bazel-testlogs/examples/tmpdir/tmpdir_test/test.xml -
```
<!-- end -->
