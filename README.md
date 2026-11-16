# pytest-bazel

![standards](https://imgs.xkcd.com/comics/standards.png)

[Documentation] [Changelog] [Contributing]

[documentation]: https://pytest-bazel.readthedocs.io/latest/
[changelog]: https://github.com/aignas/pytest-bazel/blob/main/CHANGELOG.md
[contributing]: https://github.com/aignas/pytest-bazel/blob/main/CONTRIBUTING.md

## Bazel test encyclopedia support

How `pytest_bazel` follows the [test encyclopedia][te] when running under
`bazel test`.

| Bazel | `pytest_bazel` | Docs | Reference |
| --- | --- | --- | --- |
| `TESTBRIDGE_TEST_ONLY` (`--test_filter`) | Selects tests with a `-k` expression, e.g. `TestClass.test_fn`, a pytest node id, or several of them separated by commas. | [Example][docs-test-filter] | [Initial conditions][te-env] |
| `TESTBRIDGE_TEST_RUNNER_FAIL_FAST` (`--test_runner_fail_fast`) | Passes `--exitfirst`. | [Example][docs-fail-fast] | [Flag][fail-fast] |
| `TEST_INFRASTRUCTURE_FAILURE_FILE` | Written when pytest itself fails, i.e. on a usage or internal error, so that a broken setup can be told apart from failing tests. | [Example][docs-infrastructure-failure] | [Initial conditions][te-env] |
| `TEST_LOGSPLITTER_OUTPUT_FILE` | Not supported. | [Not supported][not-supported] | [Initial conditions][te-env] |
| `TEST_PREMATURE_EXIT_FILE` | Created before pytest runs and removed once it returns, so tests that exit early fail. | [Example][docs-premature-exit] | [Initial conditions][te-env] |
| `TEST_RANDOM_SEED`, `TEST_RUN_NUMBER` (`--runs_per_test`) | Seeds `pytest-randomly` with `--randomly-seed`, or `random.seed` without it. | [Example][docs-runs-per-test] | [Initial conditions][te-env] |
| `TEST_SHARD_INDEX`, `TEST_TOTAL_SHARDS`, `TEST_SHARD_STATUS_FILE` (`shard_count`) | Built-in sharding: balanced shards, empty shards pass. | [Example][docs-sharding] | [Test sharding][te-sharding] |
| `TEST_SIZE` | Not supported. | [Not supported][not-supported] | [Initial conditions][te-env] |
| `TEST_TARGET` | Names the JUnit test suite, unless the pytest config sets `junit_suite_name`, and selects the package for the opt-in flags below. | [Example][docs-junit-xml] | [Initial conditions][te-env] |
| `TEST_TIMEOUT` (`timeout`, `--test_timeout`) | On timeout bazel sends SIGTERM: the stacks of all threads are printed and pytest is interrupted, so it still reports where the tests hung and writes the JUnit XML. | [Example][docs-timeout] | [Initial conditions][te-env] |
| `TEST_TMPDIR` | Used for `--basetemp` and for `TMPDIR`, `TMP` and `TEMP`, through a short alias when the path is too long for AF_UNIX sockets. | [Example][docs-tmpdir] | [Filesystem][te-fs] |
| `TEST_UNDECLARED_OUTPUTS_ANNOTATIONS_DIR` | A summary of the results and the failed tests is written as an annotation, which bazel adds to `bazel-testlogs/<target>/test.outputs_manifest/ANNOTATIONS`. | [Example][docs-annotations] | [Filesystem][te-fs] |
| `TEST_UNDECLARED_OUTPUTS_DIR` | Relative report paths of `--html`, `--json-report-file` and `--report-log` are written there. With `PYTEST_BAZEL_KEEP_FAILED_TMP_PATH=1`, so is the `tmp_path` of failed tests. | [Example][docs-keep-failed-tmp-path] | [Filesystem][te-fs] |
| `TEST_WARNINGS_OUTPUT_FILE` | Python warnings are written to it. Under `bazel test`, here and in pytest's warnings summary, the paths are relative to the runfiles root, i.e. the workspace root, so editors can open them. | [Example][docs-warnings] | [Initial conditions][te-env] |
| `XML_OUTPUT_FILE` | Passes `--junitxml`. | [Example][docs-junit-xml] | [Initial conditions][te-env] |

See [the features in the docs][features] for each of them in action.

[features]: https://pytest-bazel.readthedocs.io/latest/features/index.html

### Not supported

These parts of the test encyclopedia are out of scope for `pytest_bazel`:

* `TEST_LOGSPLITTER_OUTPUT_FILE`: a Google internal protobuf log format
  that nothing outside of Google reads.
* `TEST_SIZE`: bazel already uses the size for the timeout and the resources
  of a test, there is nothing left for the test runner to do.
* `TEST_SRCDIR`: deprecated. Tests run in the runfiles root, use the
  `runfiles` library of your rules to find files.
* `TEST_WORKSPACE`: it always names the main repository, so it does not help
  with tests from other repositories.
* Coverage (`COVERAGE_*`): collected by the Python rules, e.g. the `py_test`
  of `rules_python`, which wraps the whole test process.

[docs-annotations]: https://pytest-bazel.readthedocs.io/latest/features/annotations.html
[docs-config-from-package]: https://pytest-bazel.readthedocs.io/latest/features/config-from-package.html
[docs-fail-fast]: https://pytest-bazel.readthedocs.io/latest/features/fail-fast.html
[docs-infrastructure-failure]: https://pytest-bazel.readthedocs.io/latest/features/infrastructure-failure.html
[docs-junit-xml]: https://pytest-bazel.readthedocs.io/latest/features/junit-xml.html
[docs-junit-output]: https://pytest-bazel.readthedocs.io/latest/features/junit-output.html
[docs-keep-failed-tmp-path]: https://pytest-bazel.readthedocs.io/latest/features/keep-failed-tmp-path.html
[docs-namespace-packages]: https://pytest-bazel.readthedocs.io/latest/features/namespace-packages.html
[docs-premature-exit]: https://pytest-bazel.readthedocs.io/latest/features/premature-exit.html
[docs-runs-per-test]: https://pytest-bazel.readthedocs.io/latest/features/runs-per-test.html
[docs-scope-collection]: https://pytest-bazel.readthedocs.io/latest/features/scope-collection.html
[docs-sharding]: https://pytest-bazel.readthedocs.io/latest/features/sharding.html
[docs-test-filter]: https://pytest-bazel.readthedocs.io/latest/features/test-filter.html
[docs-timeout]: https://pytest-bazel.readthedocs.io/latest/features/timeout.html
[docs-tmpdir]: https://pytest-bazel.readthedocs.io/latest/features/tmpdir.html
[docs-warnings]: https://pytest-bazel.readthedocs.io/latest/features/warnings.html
[not-supported]: https://github.com/aignas/pytest-bazel#not-supported
[te]: https://bazel.build/reference/test-encyclopedia
[te-env]: https://bazel.build/reference/test-encyclopedia#initial-conditions
[te-fs]: https://bazel.build/reference/test-encyclopedia#test-interaction-filesystem
[te-sharding]: https://bazel.build/reference/test-encyclopedia#test-sharding
[fail-fast]: https://bazel.build/reference/command-line-reference#param-no-test-runner-fail-fast

## pytest plugins

| Plugin | `pytest_bazel` | Docs |
| --- | --- | --- |
| [pytest-randomly] | Seeded from `TEST_RANDOM_SEED` with `--runs_per_test`. | [Example][docs-runs-per-test] |
| [pytest-shard] | Not needed, sharding is built in. | [Example][docs-sharding] |
| [pytest-xdist] | Works with `tags = ["cpu:N"]`, prints the stacks of the workers on timeout. | [Example][docs-xdist] |

[pytest-randomly]: https://pypi.org/project/pytest-randomly/
[pytest-shard]: https://pypi.org/project/pytest-shard/
[pytest-xdist]: https://pypi.org/project/pytest-xdist/
[docs-xdist]: https://pytest-bazel.readthedocs.io/latest/features/xdist.html

## Guides

* [Debugging tests][docs-debugging]: `bazel test` gives the tests no terminal,
  use `bazel run` instead.
* [Retrying flaky tests][docs-retries]: with bazel or with
  `pytest-rerunfailures`, and why not both.

[docs-debugging]: https://pytest-bazel.readthedocs.io/latest/features/debugging.html
[docs-retries]: https://pytest-bazel.readthedocs.io/latest/features/retries.html

## Performance

What `pytest_bazel` adds to a test, measured with `bazel run //dev/benchmark`
on the machine below. [`tests/performance`][perf-tests] checks what keeps it
fast on every `bazel test //...`. Without `.pyc` files in the runfiles, which
rules_python does not build by default, every test compiles pytest again; see
[Performance][docs-performance] for how to precompile and what was made
faster.

<!-- benchmark -->
| What | Time |
| --- | --- |
| Importing pytest without / with `.pyc` files | 348 ms / 129 ms |
| Importing `pytest_bazel` on top of pytest without / with `.pyc` files | 7.1 ms / 2.0 ms |
| A run of 200 tests with `pytest --junitxml` / with `pytest_bazel` | 449 ms / 446 ms |
| `PYTEST_BAZEL_EXACT_TEST_FILTER=1` with a name, 20000 tests | 25.7 ms |
| `PYTEST_BAZEL_EXACT_TEST_FILTER=1` with 4 filters, 20000 tests | 68.0 ms |
| Splitting 20000 tests into shards | 5.3 ms |

Medians on Python 3.10.22, pytest 9.1.1, Linux x86_64, 8 CPUs.
<!-- end benchmark -->

[perf-tests]: https://github.com/aignas/pytest-bazel/blob/main/tests/performance/test_performance.py
[docs-performance]: https://pytest-bazel.readthedocs.io/latest/performance.html

## Thanks

Special thanks to [rules_python_pytest] and [rules_py] projects that had some
great ideas how to integrate with `pytest`. This attempts to [unify] all of the
approaches.

[rules_python_pytest]: https://github.com/caseyduquettesc/rules_python_pytest 
[rules_py]: https://github.com/aspect-build/rules_py/blob/main/py/private/pytest.py.tmpl
[unify]: https://xkcd.com/927/

## Planned for 1.0

Behaviour changes are added behind opt-in flags first. Their defaults will be
flipped in 1.0. Set them in the `env` of a test, or for all tests with e.g.
`test --test_env=PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE=1` in `.bazelrc`.
The options that a flag sets, e.g. `junit_logging`, are left as they are when
the pytest config file sets them. `testpaths` is only left as it is when the
config file is in the package of the target, and with
`PYTEST_BAZEL_CONFIG_FROM_PACKAGE=1` it is relative to that config file.

| Env var | Default | Default in 1.0 | Description | Docs |
| --- | --- | --- | --- | --- |
| `PYTEST_BAZEL_CONFIG_FROM_PACKAGE` | `0` | `1` | Use the pytest config file (e.g. `pytest.ini`) in the bazel package of the target or its parents. pytest only looks in the runfiles root. | [Example][docs-config-from-package] |
| `PYTEST_BAZEL_CONSIDER_NAMESPACE_PACKAGES` | `0` | `1` | Pass `-o consider_namespace_packages=true` on pytest 8.1+, so that test modules in packages without `__init__.py` do not shadow third-party packages. | [Example][docs-namespace-packages] |
| `PYTEST_BAZEL_EXACT_TEST_FILTER` | `0` | `1` | Select the tests of `--test_filter` by their exact names rather than with `-k`, which matches substrings, e.g. `test_add` would also run `test_add_many`. | [Example][docs-test-filter] |
| `PYTEST_BAZEL_JUNIT_OUTPUT` | `0` | `1` | Add the stdout, stderr and logs of failed tests to the JUnit XML, which CI shows. | [Example][docs-junit-output] |
| `PYTEST_BAZEL_KEEP_FAILED_TMP_PATH` | `0` | `1` | Keep the `tmp_path` of failed tests in `TEST_UNDECLARED_OUTPUTS_DIR`, i.e. in `bazel-testlogs/<target>/test.outputs`. Needs pytest 7.3+. | [Example][docs-keep-failed-tmp-path] |
| `PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE` | `0` | `1` | Only collect tests from the bazel package of the target when no paths are passed. | [Example][docs-scope-collection] |
