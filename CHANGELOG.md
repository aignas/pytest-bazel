# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

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

[unreleased]: https://github.com/aignas/pytest-bazel/compare/0.3.0...HEAD
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
