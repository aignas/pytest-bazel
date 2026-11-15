# Guidance for agents

`pytest-bazel` is a pytest wrapper that makes pytest follow the Bazel
[test encyclopedia](https://bazel.build/reference/test-encyclopedia). It is
published to PyPI and is built and tested with Bazel.

## Building and testing

* `bazel test //...` runs all tests and builds the docs.
* `prek run --files <files>` runs ruff (lint and format), pyrefly (types)
  and `bazel mod tidy`. CI runs `prek run --all-files`.
* `docs/readthedocs_build.sh` is what Read the Docs runs. Use it with
  `READTHEDOCS=True` and the other `READTHEDOCS_*` vars to reproduce RTD
  failures.
* After changing `pyproject.toml`, run `bazel run //:lock.update`.

## Code

* The minimum Python version is 3.8. Use `typing.Optional`/`List` rather
  than `X | None`/`list[X]`, and no stdlib APIs newer than 3.8. pyrefly
  checks against 3.8.
* Use `pathlib` over `os.path`.
* Read Bazel env vars through `BazelEnv` in `pytest_bazel/main.py`, so that
  tests can pass a plain dict.
* Do not change existing behaviour unless the change needs it. Put
  behaviour changes behind an opt-in `PYTEST_BAZEL_*` env var (`0` or `1`,
  read with `_flag`) and add it to the "Planned for 1.0" table in
  `docs/index.md`.

## Tests

* Write tests with pytest, not unittest, and run them with our own runner
  by ending the file with `if __name__ == "__main__": pytest_bazel.main()`
  and adding `//pytest_bazel` to `deps`.
* Every change needs tests. Test the args from `_pytest_args` and, if the
  behaviour depends on pytest, run them with `pytester`.
* If the behaviour depends on Bazel (env vars, runfiles, sandbox), add a test
  that runs under `bazel test` and check that it fails without the change.
* Put new tests in their own package under `tests/` to avoid conflicts in
  `tests/main/BUILD.bazel`.

## Commits and PRs

Use [Conventional Commits](https://www.conventionalcommits.org/):
`type(scope)!: summary`.

* `fix:` and `feat:` are for user-visible changes only.
* `docs:`, `test:`, `refactor:`, `build:` (packaging, release, dev tooling),
  `ci:` (`.github/workflows`), `chore:` for the rest.
* Breaking changes need `!` and a `BREAKING CHANGE: <summary>` footer.

The PR description becomes the commit message on merge, so write it as one:

* Say *why* the change is made (how the bug shows up, or what cannot be done
  without it) and *how*, at a high level. A few short paragraphs at most.
* Omit needless words. Wrap at 72 columns. No headings in small PRs.
* No per-file change lists, test logs, checklists or emoji.
* No AI disclosure lines, "Generated with" footers or `Co-Authored-By`
  trailers for AI tools.
* Link related issues, e.g. `Fixes #12` or `Work towards #12`.

Example:

```
fix: point TMPDIR at TEST_TMPDIR

Bazel exports TEST_TMPDIR but not TMPDIR, so `tempfile` used the
shared /tmp. That is not hermetic and fails on remote execution
workers that mount /tmp as noexec.

Set TMPDIR, TMP and TEMP to TEST_TMPDIR before running pytest.
```

Once a PR is under review, push new commits instead of amending or
rebasing.

## News entries

User-visible changes need a `news/<PR number>.<category>.md` file, where
`<category>` is one of `added`, `changed`, `fixed` or `removed`. Write one or
two sentences about the behaviour, without implementation details or a
leading bullet. They are collected into `CHANGELOG.md` on release.
