# Performance

`pytest_bazel` runs in every test process, so what it adds is paid once per
test target, or once per collected test for the code that looks at each test.
The [README](https://github.com/aignas/pytest-bazel#performance) has the
current numbers, measured with `bazel run //dev/benchmark`.

## Faster test startup with precompiled Python

The largest cost of a short test is not `pytest_bazel` but compiling Python.
Without `.pyc` files in the runfiles, every test process compiles `pytest` and
its other deps from source, and bazel throws the compiled files away after the
test. On a Linux machine with Python 3.13, importing pytest takes ~400 ms
without `.pyc` files and ~120 ms with them.

rules_python can compile the sources at build time, where bazel caches the
`.pyc` files like any other output. Packages from pip are not compiled by
default, so it needs `force_enabled`:

```
# .bazelrc
common --@rules_python//python/config_settings:precompile=force_enabled
```

In this repository, that made short test targets ~0.6 s faster, e.g. 2.2 s
instead of 2.8 s on average, and cut the sum of the test times of
`bazel test //...` from 167 s to 123 s.

:::{warning}
With rules_python 2.5.1, `force_enabled` fails the analysis of a `py_test`
that uses `main_module` without a main file, e.g.
`main_module = "pytest_bazel"`, with `key None not found in dictionary`.
[bazel-contrib/rules_python#4403](https://github.com/bazel-contrib/rules_python/pull/4403)
fixes it, until it is released, apply it as a patch with
`single_version_override` like this repository does in `MODULE.bazel`, or use
a test file that calls `pytest_bazel.main()` for those targets.
:::

## What was made faster

Each of these is checked by `tests/performance` on every `bazel test //...`,
without timings, which would be flaky.

### The exact test filter is parsed once

With `PYTEST_BAZEL_EXACT_TEST_FILTER=1`, a plugin compares the filter with the
node id of every collected test. It used to split the filter character by
character for every test, and to compare a path at every character of the
node id. With 20000 tests, a filter by name took ~320 ms and four comma
separated filters ~980 ms.

Now the filter is parsed once per session. A test can only match if every
name of the filter occurs in its node id, which a fast substring check rules
out for most tests before the node id is split into names, and paths are only
compared where they occur in the node id. The same filters take ~16 ms and
~41 ms, and select the same tests.

### Importing `pytest_bazel` loads less

Every test process imports `pytest_bazel`, on top of pytest that it needs
anyway. That took 7.1 ms, most of it to import `configparser` and `tomllib`,
which read the pytest config file that most tests do not have. They are now
imported only when a config file is read. `BazelEnv` is a plain class rather
than a dataclass, which took ~0.4 ms to create. Importing `pytest_bazel` now
takes ~1.5 ms on top of pytest with `.pyc` files, see above for without.

### What was measured and left as it is

- Splitting 20000 tests into shards takes ~5 ms.
- Building the pytest args takes ~1 ms, also with 150 entries on `sys.path`.
- Writing warnings to `TEST_WARNINGS_OUTPUT_FILE` is dominated by Python
  formatting them. Flushing each warning, which keeps the file complete if
  bazel kills the test, takes ~1 µs.
- Against `pytest --junitxml`, which bazel needs either way, `pytest_bazel`
  adds ~10 ms to a run of 200 tests, mostly to load its plugins.

## Keeping it fast

- `tests/performance` checks what the speed-ups rely on, e.g. that importing
  `pytest_bazel` loads no config file parsers, and that the filter is parsed
  once. Each check fails on the code before its speed-up.
- `bazel run //dev/benchmark` measures the timings on the current machine,
  and `bazel run //dev/benchmark -- --update` writes them to `README.md`. Run
  it after changes that may affect the speed.
