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
  test_filter_exact:
    target: '//examples/test_filter:test_filter_test'
    flags: ['--test_filter=TestMath.test_add', '--test_env=PYTEST_BAZEL_EXACT_TEST_FILTER=1']
    keep: 'collected|passed'
---

# Selecting tests with `--test_filter`

`bazel test --test_filter=...` is passed to pytest as a `-k` expression.
`TestClass.test_fn`, `TestClass::test_fn` and pytest node ids such as
`path/to/test_file.py::TestClass::test_fn` select a test, but as `-k`
matches substrings, also e.g. `test_fn_other`, see [Exact names](#exact-names). A filter
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

    def test_add_many(self):
        assert 1 + 1 + 1 == 3

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
collected 4 items / 2 deselected / 2 selected

examples/test_filter/test_filter.py ..                                   [100%]

- generated xml file: bazel-testlogs/examples/test_filter/test_filter_test/test.xml -
======================= 2 passed, 2 deselected in <time> ========================
```
<!-- end -->

Separate several tests with commas:

<!-- run: test_filter_commas -->
```console
$ bazel test //examples/test_filter:test_filter_test --test_filter=TestMath.test_add,test_other
//examples/test_filter:test_filter_test PASSED in <time>
$ cat bazel-testlogs/examples/test_filter/test_filter_test/test.log
collected 4 items / 1 deselected / 3 selected
======================= 3 passed, 1 deselected in <time> ========================
```
<!-- end -->

When a filter selects no tests in a target, the target passes, so that
`bazel test //... --test_filter=...` works.

## Exact names

`-k` matches substrings of the names of a test and of its parents, so above
`TestMath.test_add` also runs `test_add_many`, and `test_add` would run every
test in a `test_add.py`. Opt-in with `PYTEST_BAZEL_EXACT_TEST_FILTER=1`, which
will be the default in 1.0, each name in the filter has to be the name of the
test, of one of its classes, of its module or of a directory of its path, in
that order. `test_x` selects all the parameters of a parametrized test,
`test_x[1]` only one. A filter with a `/` or ending in `.py` is a path, e.g.
`pkg/sub` selects the tests in that directory. A filter with spaces is still
a `-k` expression.

<!-- run: test_filter_exact -->
```console
$ bazel test //examples/test_filter:test_filter_test --test_filter=TestMath.test_add --test_env=PYTEST_BAZEL_EXACT_TEST_FILTER=1
//examples/test_filter:test_filter_test PASSED in <time>
$ cat bazel-testlogs/examples/test_filter/test_filter_test/test.log
collected 4 items / 3 deselected / 1 selected
======================= 1 passed, 3 deselected in <time> ========================
```
<!-- end -->
