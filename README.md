# pytest-bazel

![standards](https://imgs.xkcd.com/comics/standards.png)

[Documentation] [Changelog] [Contributing]

[documentation]: https://pytest-bazel.readthedocs.io/
[changelog]: https://github.com/aignas/pytest-bazel/blob/main/CHANGELOG.md
[contributing]: https://github.com/aignas/pytest-bazel/blob/main/CONTRIBUTING.md

## Bazel test encyclopedia support

How `pytest_bazel` follows the [test encyclopedia][te] when running under
`bazel test`.

| Bazel | `pytest_bazel` | Reference |
| --- | --- | --- |
| `TESTBRIDGE_TEST_ONLY` (`--test_filter`) | Selects tests with a `-k` expression, e.g. `TestClass.test_fn` or a pytest node id. | [Initial conditions][te-env] |
| `TESTBRIDGE_TEST_RUNNER_FAIL_FAST` (`--test_runner_fail_fast`) | Passes `--exitfirst`. | [Flag][fail-fast] |
| `TEST_INFRASTRUCTURE_FAILURE_FILE` | Written when pytest itself fails, i.e. on a usage or internal error, so that a broken setup can be told apart from failing tests. | [Initial conditions][te-env] |
| `TEST_LOGSPLITTER_OUTPUT_FILE` | Not supported. | [Initial conditions][te-env] |
| `TEST_PREMATURE_EXIT_FILE` | Created before pytest runs and removed once it returns, so tests that exit early fail. | [Initial conditions][te-env] |
| `TEST_RANDOM_SEED`, `TEST_RUN_NUMBER` (`--runs_per_test`) | Seeds `pytest-randomly` with `--randomly-seed`, or `random.seed` without it. | [Initial conditions][te-env] |
| `TEST_SHARD_INDEX`, `TEST_TOTAL_SHARDS`, `TEST_SHARD_STATUS_FILE` (`shard_count`) | Built-in sharding: balanced shards, empty shards pass. | [Test sharding][te-sharding] |
| `TEST_SIZE` | Not supported. | [Initial conditions][te-env] |
| `TEST_TARGET` | Names the JUnit test suite, and selects the package for the opt-in flags below. | [Initial conditions][te-env] |
| `TEST_TIMEOUT` (`timeout`, `--test_timeout`) | On timeout bazel sends SIGTERM: the stacks of all threads are printed and pytest is interrupted, so it still reports where the tests hung and writes the JUnit XML. | [Initial conditions][te-env] |
| `TEST_TMPDIR` | Used for `--basetemp` and for `TMPDIR`, `TMP` and `TEMP`, through a short alias when the path is too long for AF_UNIX sockets. | [Filesystem][te-fs] |
| `TEST_UNDECLARED_OUTPUTS_ANNOTATIONS_DIR` | Not supported yet. | [Filesystem][te-fs] |
| `TEST_UNDECLARED_OUTPUTS_DIR` | Relative report paths of `--html`, `--json-report-file` and `--report-log` are written there. With `PYTEST_BAZEL_KEEP_FAILED_TMP_PATH=1`, so is the `tmp_path` of failed tests. | [Filesystem][te-fs] |
| `TEST_WARNINGS_OUTPUT_FILE` | Python warnings are written to it. | [Initial conditions][te-env] |
| `XML_OUTPUT_FILE` | Passes `--junitxml`. | [Initial conditions][te-env] |

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

[te]: https://bazel.build/reference/test-encyclopedia
[te-env]: https://bazel.build/reference/test-encyclopedia#initial-conditions
[te-fs]: https://bazel.build/reference/test-encyclopedia#test-interaction-filesystem
[te-sharding]: https://bazel.build/reference/test-encyclopedia#test-sharding
[fail-fast]: https://bazel.build/reference/command-line-reference#param-no-test-runner-fail-fast

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

| Env var | Default | Default in 1.0 | Description |
| --- | --- | --- | --- |
| `PYTEST_BAZEL_CONFIG_FROM_PACKAGE` | `0` | `1` | Use the pytest config file (e.g. `pytest.ini`) in the bazel package of the target or its parents. pytest only looks in the runfiles root. |
| `PYTEST_BAZEL_CONSIDER_NAMESPACE_PACKAGES` | `0` | `1` | Pass `-o consider_namespace_packages=true` on pytest 8.1+, so that test modules in packages without `__init__.py` do not shadow third-party packages. |
| `PYTEST_BAZEL_KEEP_FAILED_TMP_PATH` | `0` | `1` | Keep the `tmp_path` of failed tests in `TEST_UNDECLARED_OUTPUTS_DIR`, i.e. in `bazel-testlogs/<target>/test.outputs`. Needs pytest 7.3+. |
| `PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE` | `0` | `1` | Only collect tests from the bazel package of the target when no paths are passed. |
