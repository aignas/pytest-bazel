---
# The examples that dev/update_docs runs for the `run` blocks below.
pytest_bazel_examples:
  test_filter:
    target: '//examples/test_filter:test_filter_test'
    flags: ['--test_filter=TestMath.test_add']
  test_filter_commas:
    target: '//examples/test_filter:test_filter_test'
    flags: ['--test_filter=TestMath.test_add,test_other']
    keep: 'collected|passed'
---

# Selecting tests with `--test_filter`

`bazel test --test_filter=...` is passed to pytest as a `-k` expression.
`TestClass.test_fn`, `TestClass::test_fn` and pytest node ids such as
`path/to/test_file.py::TestClass::test_fn` select a single test. A filter
with spaces, e.g. `--test_filter="add or sub"`, is used as a `-k` expression
as it is. A `-k` in the `args` of the target still applies, the filter is
combined with it.

A target where the filter selects no tests passes, so that
`bazel test //... --test_filter=...` works, but says so in its log.

<!-- source: examples/test_filter/test_filter.py -->
```{code-block} python
:caption: examples/test_filter/test_filter.py

class TestMath:
    def test_add(self):
        assert 1 + 1 == 2

    def test_sub(self):
        assert 2 - 1 == 1


def test_other():
    pass


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- run: test_filter -->
```console
$ bazel test //examples/test_filter:test_filter_test --test_filter=TestMath.test_add
//examples/test_filter:test_filter_test PASSED in <time>
$ cat bazel-testlogs/examples/test_filter/test_filter_test/test.log
============================= test session starts ==============================
collected 3 items / 2 deselected / 1 selected

examples/test_filter/test_filter.py .                                    [100%]

- generated xml file: bazel-testlogs/examples/test_filter/test_filter_test/test.xml -
======================= 1 passed, 2 deselected in <time> ========================
```
<!-- end -->

Separate several tests with commas:

<!-- run: test_filter_commas -->
```console
$ bazel test //examples/test_filter:test_filter_test --test_filter=TestMath.test_add,test_other
//examples/test_filter:test_filter_test PASSED in <time>
$ cat bazel-testlogs/examples/test_filter/test_filter_test/test.log
collected 3 items / 1 deselected / 2 selected
======================= 2 passed, 1 deselected in <time> ========================
```
<!-- end -->

When a filter selects no tests in a target, the target passes, so that
`bazel test //... --test_filter=...` works.
