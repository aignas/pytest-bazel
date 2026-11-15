# Random seeds with `--runs_per_test`

With `--runs_per_test`, bazel gives each run its own `TEST_RANDOM_SEED`.
`pytest_bazel` passes it to [pytest-randomly] as `--randomly-seed`, which
seeds `random` and shuffles the tests, so that each run is different but can
be repeated. Without `pytest-randomly`, `random` is seeded with it.

<!-- source: examples/runs_per_test/test_runs_per_test.py -->
```{code-block} python
:caption: examples/runs_per_test/test_runs_per_test.py

import random


def test_random():
    print("random number:", random.randint(0, 100))


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- run: runs_per_test -->
```console
$ bazel test //examples/runs_per_test:runs_per_test_test --runs_per_test=3 --test_arg=-s
//examples/runs_per_test:runs_per_test_test PASSED in <time>
$ cat bazel-testlogs/examples/runs_per_test/runs_per_test_test/run_1_of_3/test.log
Using --randomly-seed=1
examples/runs_per_test/test_runs_per_test.py random number: 49
$ cat bazel-testlogs/examples/runs_per_test/runs_per_test_test/run_2_of_3/test.log
Using --randomly-seed=2
examples/runs_per_test/test_runs_per_test.py random number: 38
$ cat bazel-testlogs/examples/runs_per_test/runs_per_test_test/run_3_of_3/test.log
Using --randomly-seed=3
examples/runs_per_test/test_runs_per_test.py random number: 93
```
<!-- end -->

[pytest-randomly]: https://pypi.org/project/pytest-randomly/
