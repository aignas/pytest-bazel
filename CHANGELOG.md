# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased

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

[unreleased]: https://github.com/aignas/pytest-bazel/compare/0.0.7...HEAD
[0.0.7]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.7
[0.0.6]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.6
[0.0.4]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.4
[0.0.3]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.3
[0.0.2]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.2
[0.0.1]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.1
[0.0.0]: https://github.com/aignas/pytest-bazel/releases/tag/0.0.0
