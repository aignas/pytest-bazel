# Guidance for agents

`pytest-bazel` is a pytest wrapper that makes pytest follow the Bazel
[test encyclopedia](https://bazel.build/reference/test-encyclopedia). It is
published to PyPI and is built and tested with Bazel.

## Building and testing

* `bazel test //...` runs all tests and builds the docs.
* CI also runs `bazel test //...` on Python 3.9 to 3.15 with
  `--@rules_python//python/config_settings:python_version=3.X`.
* `prek run --files <files>` runs ruff (lint and format), pyrefly (types)
  and `bazel mod tidy`. CI runs `prek run --all-files`.
* `docs/readthedocs_build.sh` is what Read the Docs runs. Use it with
  `READTHEDOCS=True` and the other `READTHEDOCS_*` vars to reproduce RTD
  failures.
* After changing `pyproject.toml`, run `bazel run //:lock.update`.
* CI checks that the docs are up to date, see [Docs](#docs).

## Code

* Support the Python versions that rules_python supports, currently 3.9+.
  Use `typing.Optional` rather than `X | None` and no stdlib APIs newer
  than 3.9. pyrefly checks against 3.9.
* Use `pathlib` over `os.path`.
* Read Bazel env vars through `BazelEnv` in `pytest_bazel/main.py`, so that
  tests can pass a plain dict.
* Do not change existing behaviour unless the change needs it. Put
  behaviour changes behind an opt-in `PYTEST_BAZEL_*` env var (`0` or `1`,
  read with `_flag`) and add it to the "Planned for 1.0" table at the
  bottom of `README.md`.

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

## Docs

`docs/features/*.md` show each feature in action with the output of the
examples in `examples/`. `dev/update_docs.py` runs the examples and writes
the blocks between `<!-- source: <file> -->` or `<!-- run: <example> -->` and
`<!-- end -->`. CI runs `dev/update_docs.py --check`, which fails when a page
is out of date.

* Run `dev/update_docs.py` and commit the pages after any change that can
  change the output of `bazel test`: the code of `pytest_bazel`, an example,
  or a bump of pytest or rules_python. Run it after staging other changes, and
  stage the pages again.
* After rebasing a PR or merging `main` into it, run `dev/update_docs.py`
  again, as the changes on `main` can change the output.
* Do not edit the generated blocks by hand, only the text around them.
* Every feature in the tables of `README.md` needs a page:
  * An example package `examples/<feature>/`. Tag its targets `manual`, as
    examples may fail on purpose and `bazel test //...` must stay green.
  * A `docs/features/<feature>.md` page with a short explanation and the
    blocks. Opt-in features say that they will be the default in 1.0.
  * An entry in `EXAMPLES` in `dev/update_docs.py`. Use `keep` to show only
    the lines that matter, and leave out lines that change with unrelated
    changes, e.g. line numbers in `pytest_bazel` or rules_python.
* The output must be the same on every run and machine. If `--check` is
  flaky, add a rule to `_SANITIZE` or `_DROP` instead of hiding the
  difference with `keep`.
* Also update the tables at the bottom of `README.md` when adding, changing
  or removing a feature or an opt-in flag.

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

Before tagging a release, move the news entries into a `## [<version>]`
section of `CHANGELOG.md`, add its `releases/tag` link and update the
`[unreleased]` link. The release workflow runs `pkg/check_changelog.py
<version>` and fails without publishing if any of that is missing.
