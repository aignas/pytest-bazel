---
# The examples that dev/update_docs runs for the `run` blocks below.
pytest_bazel_examples:
  sharding:
    target: '//examples/sharding:sharding_test'
    files: ['shard_*_of_3/test.log']
    keep: '^collected|passed'
  more_shards_than_tests:
    target: '//examples/sharding:more_shards_than_tests_test'
    files: ['shard_*_of_8/test.log']
    keep: 'passed|deselected'
---

# Sharding with `shard_count`

When a test has `shard_count`, bazel runs it in several processes and
`pytest_bazel` gives each of them a part of the tests. `pytest-shard` is not
needed. The tests are sorted by their node id and dealt out to the shards in
turn, so the shards differ in size by at most one test.

<!-- source: examples/sharding/test_sharding.py -->
```{code-block} python
:caption: examples/sharding/test_sharding.py

import pytest


@pytest.mark.parametrize("n", range(5))
def test_number(n):
    pass


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- source: examples/sharding/BUILD.bazel -->
```{code-block} starlark
:caption: examples/sharding/BUILD.bazel

load("@rules_python//python:py_test.bzl", "py_test")

py_test(
    name = "sharding_test",
    srcs = ["test_sharding.py"],
    main = "test_sharding.py",
    shard_count = 3,
    tags = ["manual"],
    deps = ["//pytest_bazel"],
)

# More shards than tests, some shards get no tests.
py_test(
    name = "more_shards_than_tests_test",
    srcs = ["test_sharding.py"],
    main = "test_sharding.py",
    shard_count = 8,
    tags = ["manual"],
    deps = ["//pytest_bazel"],
)
```
<!-- end -->

<!-- run: sharding -->
```console
$ bazel test //examples/sharding:sharding_test
//examples/sharding:sharding_test PASSED in <time>
$ cat bazel-testlogs/examples/sharding/sharding_test/shard_1_of_3/test.log
collected 5 items / 3 deselected / 2 selected
======================= 2 passed, 3 deselected in <time> ========================
$ cat bazel-testlogs/examples/sharding/sharding_test/shard_2_of_3/test.log
collected 5 items / 3 deselected / 2 selected
======================= 2 passed, 3 deselected in <time> ========================
$ cat bazel-testlogs/examples/sharding/sharding_test/shard_3_of_3/test.log
collected 5 items / 4 deselected / 1 selected
======================= 1 passed, 4 deselected in <time> ========================
```
<!-- end -->

Shards that get no tests, because there are more shards than tests, pass:

<!-- run: more_shards_than_tests -->
```console
$ bazel test //examples/sharding:more_shards_than_tests_test
//examples/sharding:more_shards_than_tests_test PASSED in <time>
$ cat bazel-testlogs/examples/sharding/more_shards_than_tests_test/shard_1_of_8/test.log
collected 5 items / 4 deselected / 1 selected
======================= 1 passed, 4 deselected in <time> ========================
$ cat bazel-testlogs/examples/sharding/more_shards_than_tests_test/shard_2_of_8/test.log
collected 5 items / 4 deselected / 1 selected
======================= 1 passed, 4 deselected in <time> ========================
$ cat bazel-testlogs/examples/sharding/more_shards_than_tests_test/shard_3_of_8/test.log
collected 5 items / 4 deselected / 1 selected
======================= 1 passed, 4 deselected in <time> ========================
$ cat bazel-testlogs/examples/sharding/more_shards_than_tests_test/shard_4_of_8/test.log
collected 5 items / 4 deselected / 1 selected
======================= 1 passed, 4 deselected in <time> ========================
$ cat bazel-testlogs/examples/sharding/more_shards_than_tests_test/shard_5_of_8/test.log
collected 5 items / 4 deselected / 1 selected
======================= 1 passed, 4 deselected in <time> ========================
$ cat bazel-testlogs/examples/sharding/more_shards_than_tests_test/shard_6_of_8/test.log
collected 5 items / 5 deselected / 0 selected
============================ 5 deselected in <time> =============================
$ cat bazel-testlogs/examples/sharding/more_shards_than_tests_test/shard_7_of_8/test.log
collected 5 items / 5 deselected / 0 selected
============================ 5 deselected in <time> =============================
$ cat bazel-testlogs/examples/sharding/more_shards_than_tests_test/shard_8_of_8/test.log
collected 5 items / 5 deselected / 0 selected
============================ 5 deselected in <time> =============================
```
<!-- end -->
