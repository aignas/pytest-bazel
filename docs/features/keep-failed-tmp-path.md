---
# The examples that dev/update_docs runs for the `run` blocks below.
pytest_bazel_examples:
  keep_failed_tmp_path:
    target: '//examples/keep_failed_tmp_path:keep_failed_tmp_path_test'
    keep: '^FAILED|failed'
    list_dirs: ['test.outputs']
---

# Keeping the files of failed tests

Opt-in with `PYTEST_BAZEL_KEEP_FAILED_TMP_PATH=1`, this will be the default in
1.0. The `tmp_path` of failed tests is kept in the undeclared outputs of the
test, so that you can look at the files after the test.

<!-- source: examples/keep_failed_tmp_path/BUILD.bazel -->
```{code-block} starlark
:caption: examples/keep_failed_tmp_path/BUILD.bazel

load("@rules_python//python:py_test.bzl", "py_test")

py_test(
    name = "keep_failed_tmp_path_test",
    srcs = ["test_keep_failed_tmp_path.py"],
    main = "test_keep_failed_tmp_path.py",
    env = {"PYTEST_BAZEL_KEEP_FAILED_TMP_PATH": "1"},
    tags = ["manual"],
    deps = ["//pytest_bazel"],
)
```
<!-- end -->

<!-- source: examples/keep_failed_tmp_path/test_keep_failed_tmp_path.py -->
```{code-block} python
:caption: examples/keep_failed_tmp_path/test_keep_failed_tmp_path.py

def test_passes(tmp_path):
    (tmp_path / "passed.txt").write_text("not kept")


def test_fails(tmp_path):
    out = tmp_path / "failed.txt"
    out.write_text("kept for debugging")
    assert out.read_text() == "something else"


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- run: keep_failed_tmp_path -->
```console
$ bazel test //examples/keep_failed_tmp_path:keep_failed_tmp_path_test
//examples/keep_failed_tmp_path:keep_failed_tmp_path_test FAILED in <time>
$ cat bazel-testlogs/examples/keep_failed_tmp_path/keep_failed_tmp_path_test/test.log
examples/keep_failed_tmp_path/test_keep_failed_tmp_path.py .F            [100%]
tmp_path = PosixPath('bazel-testlogs/examples/keep_failed_tmp_path/keep_failed_tmp_path_test/test.outputs/pytest/test_fails0')
        out = tmp_path / "failed.txt"
examples/keep_failed_tmp_path/test_keep_failed_tmp_path.py:8: AssertionError
- generated xml file: bazel-testlogs/examples/keep_failed_tmp_path/keep_failed_tmp_path_test/test.xml -
FAILED examples/keep_failed_tmp_path/test_keep_failed_tmp_path.py::test_fails
========================= 1 failed, 1 passed in <time> ==========================
$ find bazel-testlogs/examples/keep_failed_tmp_path/keep_failed_tmp_path_test/test.outputs -type f
bazel-testlogs/examples/keep_failed_tmp_path/keep_failed_tmp_path_test/test.outputs/pytest/test_fails0/failed.txt
```
<!-- end -->
