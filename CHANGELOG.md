# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [1.0.0]

### Changed

- Only what the `pytest_bazel` package exports, i.e. `pytest_bazel.main()`, is
  public now, together with `python -m pytest_bazel`, the `pytest_bazel` console
  script and the `PYTEST_BAZEL_*` env vars. Its other modules, e.g.
  `pytest_bazel.main`, are private.
  [#114](https://github.com/aignas/pytest-bazel/pull/114).
- The package now declares that it needs pytest 7 or newer, which it already
  did. [#121](https://github.com/aignas/pytest-bazel/pull/121).
- Selecting tests with `PYTEST_BAZEL_EXACT_TEST_FILTER=1` is about twice as
  fast, and formatting the paths of warnings under `bazel test` about three
  times. [#123](https://github.com/aignas/pytest-bazel/pull/123).
- The behaviours of `PYTEST_BAZEL_CONFIG_FROM_PACKAGE`,
  `PYTEST_BAZEL_CONSIDER_NAMESPACE_PACKAGES`, `PYTEST_BAZEL_EXACT_TEST_FILTER`,
  `PYTEST_BAZEL_JUNIT_OUTPUT`, `PYTEST_BAZEL_KEEP_FAILED_TMP_PATH` and
  `PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE` are on by default, set a flag to
  `0` to turn its behaviour off.
  [#126](https://github.com/aignas/pytest-bazel/pull/126).

### Fixed

- With `PYTEST_BAZEL_CONFIG_FROM_PACKAGE=1`, the `testpaths` of the pytest
  config file of the package are now relative to that file, e.g. `testpaths =
  tests` collects `<package>/tests`. Before, they were looked up in the runfiles
  root, so with `PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE=1` too, the tests of
  all packages were collected.
  [#112](https://github.com/aignas/pytest-bazel/pull/112).
- With `PYTEST_BAZEL_KEEP_FAILED_TMP_PATH=1`, bazel no longer fails the test
  with "not all outputs were created or valid" because of links that pytest
  leaves in the outputs, a `tmp_path_retention_policy` in the pytest config file
  wins, and nothing is kept when all tests pass.
  [#115](https://github.com/aignas/pytest-bazel/pull/115).
- With `PYTEST_BAZEL_CONFIG_FROM_PACKAGE=1`, the `conftest.py` files above the
  config file of the package, e.g. in the workspace root, are loaded again.
  [#116](https://github.com/aignas/pytest-bazel/pull/116).
- Without the bazel sandbox, e.g. on Windows, with `--spawn_strategy=local` or
  under `bazel run`, pytest no longer uses the config file and rootdir of the
  workspace above the runfiles, so the tests run as in the sandbox.
  [#117](https://github.com/aignas/pytest-bazel/pull/117).
- An invalid value of a `PYTEST_BAZEL_*` flag, e.g. `true`, is now reported as a
  usage error and an infrastructure failure, with a one line message instead of
  a traceback. [#119](https://github.com/aignas/pytest-bazel/pull/119).
- Under `bazel test`, Python and pytest no longer write `.pyc` files next to the
  sources in the runfiles, as tests may only write to `TEST_TMPDIR` and the test
  outputs. [#120](https://github.com/aignas/pytest-bazel/pull/120).
- Under `bazel test`, the paths in tracebacks stay relative to the workspace
  root when a test changes the current directory, e.g. with `monkeypatch.chdir`,
  and with `--tb=line`, so that editors can open them. Before, they were
  absolute paths into the bazel sandbox, which is gone after the test.
  [#127](https://github.com/aignas/pytest-bazel/pull/127).
- The wheel no longer contains `.pyc` files, which only the Python version that
  built it could use. [#128](https://github.com/aignas/pytest-bazel/pull/128).
- Without the sandbox, e.g. on Windows, and with test files passed as args, e.g.
  by rules_python's `pytest_test`, the `conftest.py` of the workspace root is
  loaded again and test ids are relative to the workspace root, as in the
  sandbox. [#129](https://github.com/aignas/pytest-bazel/pull/129).
- A config file passed as `-c=pytest.ini`, or after other short flags as in `-vc
  pytest.ini`, is now recognised, so that the defaults of `pytest_bazel` no
  longer override the options it sets.
  [#130](https://github.com/aignas/pytest-bazel/pull/130).
- `--test_filter` now selects parametrized tests whose parameters contain `/` or
  `::`, e.g. `--test_filter=test_url[a/b]`, and `--test_filter=test_url` selects
  all of them. Before, the `/` made the filter a path and the `::` split the
  name of the test, so these tests were not selected.
  [#131](https://github.com/aignas/pytest-bazel/pull/131).
- The pytest config files of a package and their options are now found as the
  installed pytest finds them, e.g. a `pyproject.toml` with a comment after
  `[tool.pytest.ini_options]` is no longer skipped, and `[tool.pytest]` and an
  empty `.pytest.ini` only count with pytest 9.
  [#132](https://github.com/aignas/pytest-bazel/pull/132).

## [0.5.0]

### Added

- Set `PYTEST_BAZEL_EXACT_TEST_FILTER=1` to select the tests of `--test_filter`
  by their exact names, so that e.g. `test_add` no longer also runs
  `test_add_many`. Paths select the tests of a file or a directory, and it
  takes ~16 ms for 20000 tests. This will be the default in 1.0.
  [#92](https://github.com/aignas/pytest-bazel/pull/92),
  [#98](https://github.com/aignas/pytest-bazel/pull/98),
  [#99](https://github.com/aignas/pytest-bazel/pull/99),
  [#102](https://github.com/aignas/pytest-bazel/pull/102).

### Changed

- Importing `pytest_bazel` takes ~1.5 ms on top of pytest instead of ~7 ms, as
  the config file parsers are only imported when a config file is read.
  [#100](https://github.com/aignas/pytest-bazel/pull/100),
  [#107](https://github.com/aignas/pytest-bazel/pull/107).
- The new [Performance][docs-performance] page explains how to precompile
  Python with rules_python, which makes short tests ~0.6 s faster, as without it
  every test compiles pytest again.
  [#108](https://github.com/aignas/pytest-bazel/pull/108).

[docs-performance]: https://pytest-bazel.readthedocs.io/latest/performance.html

### Fixed

- Absolute report paths of `--html`, `--json-report-file` and `--report-log` are
  no longer moved into `TEST_UNDECLARED_OUTPUTS_DIR`, and relative ones given as
  a separate argument, e.g. `--html report.html`, are now moved there too.
  [#72](https://github.com/aignas/pytest-bazel/pull/72),
  [#87](https://github.com/aignas/pytest-bazel/pull/87).
- Sharded tests no longer fail when `-k` or `-m` deselect all the tests of a
  shard, or when a shard gets no tests with pytest-xdist.
  [#82](https://github.com/aignas/pytest-bazel/pull/82).
- With pytest-randomly installed but disabled, e.g. with `-p no:randomly`,
  `--runs_per_test` and `--test_env=TEST_RANDOM_SEED` no longer fail with a
  usage error, and seed `random` instead.
  [#83](https://github.com/aignas/pytest-bazel/pull/83).
- The warnings of the tests are now written to `TEST_WARNINGS_OUTPUT_FILE`, i.e.
  `bazel-testlogs/<target>/test.warnings`, which was empty, as UTF-8.
  [#84](https://github.com/aignas/pytest-bazel/pull/84),
  [#94](https://github.com/aignas/pytest-bazel/pull/94).
- A `-k` in the `args` of a target, also in combined flags such as `-vk`, is now
  combined with `--test_filter` instead of replaced by it, a filter with a `.`
  in the parameters of a test, e.g. `test_x[0.5]`, now selects only that test,
  and a target where the filter selects no tests says so in its log.
  [#85](https://github.com/aignas/pytest-bazel/pull/85),
  [#91](https://github.com/aignas/pytest-bazel/pull/91).
- `breakpoint()` under `bazel test` now respects `PYTHONBREAKPOINT`, e.g. `0` to
  ignore it, unless Python ignores it too with `-E` or `-I`.
  [#86](https://github.com/aignas/pytest-bazel/pull/86),
  [#95](https://github.com/aignas/pytest-bazel/pull/95).
- `pytest_bazel.main(args=[])` now runs pytest without args instead of with the
  args of the process.
  [#88](https://github.com/aignas/pytest-bazel/pull/88).
- pytest-xdist workers now remove their stack file when they stop, so that a
  timeout later in the test cannot kill an unrelated process that got the PID of
  a replaced worker.
  [#89](https://github.com/aignas/pytest-bazel/pull/89),
  [#96](https://github.com/aignas/pytest-bazel/pull/96).
- The options that pytest_bazel sets, e.g. `junit_suite_name`, and the ones of
  the opt-in flags, e.g. `junit_logging`, no longer override the same options in
  the pytest config file, including `pytest.toml` and a file passed with `-c`.
  A `testpaths` only does so in a config file in the package of the target.
  [#90](https://github.com/aignas/pytest-bazel/pull/90),
  [#97](https://github.com/aignas/pytest-bazel/pull/97),
  [#101](https://github.com/aignas/pytest-bazel/pull/101).

## [0.4.0]

### Added

- Tests that exit before pytest is done, e.g. with `os._exit(0)`, now fail
  instead of passing, using `TEST_PREMATURE_EXIT_FILE`.
  [#51](https://github.com/aignas/pytest-bazel/pull/51).
- When bazel times out a test, the stacks of all threads are printed and the
  JUnit XML is still written, so it is clear where the tests hung.
  [#53](https://github.com/aignas/pytest-bazel/pull/53).
- Set `PYTEST_BAZEL_KEEP_FAILED_TMP_PATH=1` to keep the `tmp_path` of failed
  tests in the bazel test outputs. This will be the default in 1.0.
  [#55](https://github.com/aignas/pytest-bazel/pull/55).
- pytest usage and internal errors are reported to bazel as infrastructure
  failures with `TEST_INFRASTRUCTURE_FAILURE_FILE`.
  [#56](https://github.com/aignas/pytest-bazel/pull/56).
- A summary of the test results and the failed tests is written to the bazel
  test annotations in
  `bazel-testlogs/<target>/test.outputs_manifest/ANNOTATIONS`.
  [#57](https://github.com/aignas/pytest-bazel/pull/57).
- With pytest-xdist, the stacks of the workers are printed when bazel times out
  a test, and `-n auto` warns unless `PYTEST_XDIST_AUTO_NUM_WORKERS` matches the
  `cpu:N` tag of the test.
  [#63](https://github.com/aignas/pytest-bazel/pull/63).
- Set `PYTEST_BAZEL_JUNIT_OUTPUT=1` to add the stdout, stderr and logs of failed
  tests to the JUnit XML, which CI shows. This will be the default in 1.0.
  [#64](https://github.com/aignas/pytest-bazel/pull/64).
- Under `bazel test`, `--pdb`, `--trace` and `breakpoint()` fail with a message
  that says to debug with `bazel run` instead of quitting the debugger right
  away. [#65](https://github.com/aignas/pytest-bazel/pull/65).
- `--test_filter=test_a,TestClass.test_b` selects several tests.
  [#67](https://github.com/aignas/pytest-bazel/pull/67).

### Fixed

- `--test_filter=TestClass.test_fn` and pytest node ids now select the test,
  instead of selecting nothing and passing.
  [#50](https://github.com/aignas/pytest-bazel/pull/50).
- Under `bazel test`, warnings show paths relative to the workspace root instead
  of absolute paths into the bazel sandbox, so editors can open them.
  [#58](https://github.com/aignas/pytest-bazel/pull/58).
- `bazel run` of a test target keeps the absolute paths in warnings, as
  documented, instead of making them relative like `bazel test`.
  [#66](https://github.com/aignas/pytest-bazel/pull/66).

## [0.3.0]

### Added

- Set `PYTEST_BAZEL_CONSIDER_NAMESPACE_PACKAGES=1` so that test modules in bazel
  packages without `__init__.py` do not shadow third-party packages. This will
  be the default in 1.0. [#38](https://github.com/aignas/pytest-bazel/pull/38).
- Set `PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE=1` to only collect tests from
  the bazel package of the test target when no paths are passed. This will be
  the default in 1.0. [#39](https://github.com/aignas/pytest-bazel/pull/39).
- Set `PYTEST_BAZEL_CONFIG_FROM_PACKAGE=1` to use a `pytest.ini` or other pytest
  config file from the bazel package of the test. This will be the default in
  1.0. [#49](https://github.com/aignas/pytest-bazel/pull/49).

### Changed

- Sharding is built in and `pytest-shard` is no longer needed. Shards are now
  balanced to within one test of each other. The `shard` extra is kept, but
  empty. [#36](https://github.com/aignas/pytest-bazel/pull/36).

### Removed

- Python 3.8 is no longer supported. We now support the same Python versions as
  `rules_python`, currently 3.9 and newer.
  [#45](https://github.com/aignas/pytest-bazel/pull/45).

### Fixed

- Set `TMPDIR`, `TMP` and `TEMP` to `TEST_TMPDIR` under `bazel test`, so
  `tempfile` no longer writes to the shared system temp dir.
  [#34](https://github.com/aignas/pytest-bazel/pull/34).
- Point `TMPDIR` at a short alias of `TEST_TMPDIR` so that AF_UNIX sockets (e.g.
  `multiprocessing.Manager`) fit within the `sun_path` length limit.
  [#35](https://github.com/aignas/pytest-bazel/pull/35).
- Shards that get no tests, because there are more shards than tests, now pass
  instead of failing the bazel test.
  [#48](https://github.com/aignas/pytest-bazel/pull/48).

## [0.2.1]

0.2.0 was not published to PyPI because of a bug in the release
workflow, this release includes its changes.

### Added

- Name the JUnit XML test suite after the bazel target (`TEST_TARGET`).
  [#37](https://github.com/aignas/pytest-bazel/pull/37).

### Fixed

- (pkg) The `all` extra now installs `pytest-randomly` and `pytest-shard`, and
  the wheel declares `Requires-Python: >=3.8`.
  [#41](https://github.com/aignas/pytest-bazel/pull/41).

## [0.2.0]

### Fixed

- (pkg): Add installable extras to include other dependencies for sharding and
  random number setting.

## [0.1.6]

### Fixed

- Support `--runs_per_test` without `pytest-randomly` so that it is easier
  to debug flaky tests.
  [#24](https://github.com/aignas/pytest-bazel/issues/24).

## [0.1.5]

### Fixed

- Fix printing of status messages and launch parameters
  [#19](https://github.com/aignas/pytest-bazel/pull/19).
- Fix sharding support for the 0th shard
  [#20](https://github.com/aignas/pytest-bazel/pull/20).

## [0.1.4]

### Fixed

- Restore `warnings.showwarning` value after running pytest.
  [#16](https://github.com/aignas/pytest-bazel/pull/16).

## [0.1.3]

Nothing yet.

## [0.1.3]

### Added

- Support for `--test_runner_fail_fast` flag

## [0.1.2]

### Changed

- Return exit code 0 (then `bazel` will report targets as `PASSED`) if there
  are no tests collected and the test filter is specified.

### Fixed

- Backport [rules_python_pytest PR#12][backport_pr_12] to correctly handle
  filenames in test filters. Whilst doing this work, we also ensure that more
  complex filters (`'test_foo or test_bar'`) also work.

[backport_pr_12]: https://github.com/caseyduquettesc/rules_python_pytest/pull/12/files

## [0.1.1]

### Added

- [RTD](https://pytest-bazel.readthedocs.io/en/latest/) setup for publishing
  docs about the project.

## [0.1.0]

### Fixed

- Make the sharding detection implementation a little bit more robust and
  ensure that we are not telling bazel that we support sharding even if we
  don't. Sharding requires extra `pytest-shard` plugin to be present at
  runtime.

### Added

- The python code has more docstrings.
- Short-circuit and do not try to access special bazel env variables if we are
  not running under `bazel` (signified by the `TEST_BAZEL` env variable.
- Add more docs and installation guide.

## [0.0.8]

### Fixed

- Actually pass the constructed args to `pytest.main`.
- Fixed the `tmpdir` usage on Linux. It seems that `bazel` pre-creates the
  directory on Linux in the sandbox and `pytest` `tmpdir` behaviour is
  different from MacOS and it starts failing.
- Ignore tests that do not belong to the current workspace, this is achieved by
  ignoring the `external` folder at the root, which may be present if the users
  are not using `--nolegacy_external_runfiles` or somewhere deeper in the tree
  if they are using rules that create a `py_library` like target from a `whl`,
  which happens to extract files into a `site-packages` directory. This makes
  the discovery robust enough to allow `pytest` to do its job itself and not
  need to provide the filenames to test manually.

## [0.0.7]

### Fixed

- Fix the version bumping in the PyPI package when making a new release.

## [0.0.6]

### Fixed

- Add a script for bumping the version number so that there is less chance to
  make mistakes.

## [0.0.4]

### Fixed

- CI for generating release notes.

## [0.0.3]

### Added

- Support `TEST_WARNINGS_OUTPUT_FILE` is used to output `warnings.warn` usage.
- Support `TEST_TMPDIR` to set the base tmpdir that affects the `tmpdir` fixture.
- Support setting the random number seed via `TEST_RANDOM_SEED` or
  `TEST_RUN_NUMBER`, whichever is present when executing.

## [0.0.2]

### Added

- Code import from `rules_python_pytest`.

### Fixed

- CI/CD to PyPI. 0.0.1 publish never worked because the GH action is running
  inside a docker image and it did not see the built artifacts.

## [0.0.1]

### Added

- Initial project scaffold.
- CI/CD pipeline to PyPI using Trusted Publishers.
- A simple test that is currently failing.

[unreleased]: https://github.com/aignas/pytest-bazel/compare/1.0.0...HEAD
[1.0.0]: https://github.com/aignas/pytest-bazel/releases/tag/1.0.0
[0.5.0]: https://github.com/aignas/pytest-bazel/releases/tag/0.5.0
[0.4.0]: https://github.com/aignas/pytest-bazel/releases/tag/0.4.0
[0.3.0]: https://github.com/aignas/pytest-bazel/releases/tag/0.3.0
[0.2.1]: https://github.com/aignas/pytest-bazel/releases/tag/0.2.1
[0.2.0]: https://github.com/aignas/pytest-bazel/releases/tag/0.2.0
[0.1.6]: https://github.com/aignas/pytest-bazel/releases/tag/0.1.6
[0.1.5]: https://github.com/aignas/pytest-bazel/releases/tag/0.1.5
[0.1.4]: https://github.com/aignas/pytest-bazel/releases/tag/0.1.4
[0.1.3]: https://github.com/aignas/pytest-bazel/releases/tag/0.1.3
[0.1.3]: https://github.com/aignas/pytest-bazel/releases/tag/0.1.3
[0.1.2]: https://github.com/aignas/pytest-bazel/releases/tag/0.1.2
[0.1.1]: https://github.com/aignas/pytest-bazel/releases/tag/0.1.1
[0.1.0]: https://github.com/aignas/pytest-bazel/releases/tag/0.1.0
[0.0.8]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.8
[0.0.7]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.7
[0.0.6]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.6
[0.0.4]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.4
[0.0.3]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.3
[0.0.2]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.2
[0.0.1]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.1
[0.0.0]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.0
