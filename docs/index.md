# `pytest` and `bazel` integration

A [pytest] wrapper to better integrate with `bazel` and it should work equally
well with any python rule set. If it does not work well, consider
[contributing].

## Features

Features ported from [rules_python_pytest]:
- Basic ignoring of external directories.
- Support for pytest 8.0 and pytest 7.0 and handle running of tests when
  passing the filenames to the runner.
- Test sharding support, which used to need [pytest-shard] and is now built
  in.
- Supporting filtering tests via `bazel test --test_filter <target>`.

Features ported from [rules_py]:
- Use `-p no:cacheprovider`

[pytest-shard]: https://pypi.org/project/pytest-shard/

Extra features implementing [test_encyclopedia] spec:
- `TEST_WARNINGS_OUTPUT_FILE` is used to output `warnings.warn` usage.
- `TEST_TMPDIR` is used
- `TEST_RANDOM_SEED` is used for predictive tests, consider integrating with https://pypi.org/project/pytest-randomly/.
- `TESTBRIDGE_TEST_RUNNER_FAIL_FAST` is used to stop execution upon first failure (enabled by `--test_runner_fail_fast` flag).
- short circuit if not running under bazel (see `BAZEL_TEST` env var).

Extras that have tests:
- No passing of files as args is needed. Pytest discovery is working as
  expected. Set `PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE=1` to only collect
  the tests in the bazel package of the test target, so that tests of other
  packages that are in the runfiles via `deps` or `data` are not collected.
  Passing paths as args overrides this. This will be the default in 1.0,
  see [Planned for 1.0][planned-1.0].

[test_encyclopedia]: https://bazel.build/reference/test-encyclopedia
[planned-1.0]: https://github.com/aignas/pytest-bazel#planned-for-10

## Thanks

Special thanks to [rules_python_pytest] and [rules_py] projects that had some
great ideas how to integrate with `pytest`. This attempts to [unify] all of the
approaches.

[rules_python_pytest]: https://github.com/caseyduquettesc/rules_python_pytest 
[rules_py]: https://github.com/aspect-build/rules_py/blob/main/py/private/pytest.py.tmpl
[unify]: https://xkcd.com/927/
[pytest]: https://pypi.org/project/pytest


```{toctree}
:hidden:
self
Usage <usage>
Features <features/index>
Performance <performance>
Changelog <changelog>
Contributing <contributing>
```
