"""Measure how much time pytest_bazel adds to a test.

`bazel test //tests/performance` checks what keeps pytest_bazel fast without
timings, which would be flaky. This measures the timings on this machine, to
run by hand after changes that may affect them:

    bazel run //dev/benchmark             # print the results
    bazel run //dev/benchmark -- --update # also write them to README.md

The results go to the block between `<!-- benchmark -->` and
`<!-- end benchmark -->` in README.md.
"""

import argparse
import compileall
import importlib.util
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import timeit
from pathlib import Path
from typing import Callable, Optional

import pytest

# The directory of this file is on sys.path, see BUILD.bazel.
from lib import ReadmeError, node_ids, replace_block, table

from pytest_bazel.exact_filter import _Filter
from pytest_bazel.shard import select_shard

_TESTS = 20_000
_SUITE_TESTS = 200


def _median_ms(fn: Callable[[], object], repeat: int) -> float:
    """Return the median time of `fn` in milliseconds."""
    return statistics.median(timeit.repeat(fn, number=1, repeat=repeat)) * 1000


def _python(*args: str, cwd: Optional[Path] = None, **env: str) -> str:
    """Run Python with the sys.path of this process, return its stdout."""
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path), **env},
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def run_overhead_ms(repeat: int = 7) -> tuple[float, float]:
    """Return the time of a test process with pytest and with pytest_bazel.

    pytest writes the JUnit XML too, as bazel needs it either way.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "test_suite.py").write_text(
            "import pytest\n\n"
            f"@pytest.mark.parametrize('n', range({_SUITE_TESTS}))\n"
            "def test_n(n):\n    pass\n"
        )
        (root / "tmp").mkdir()
        bazel_env = {
            "BAZEL_TEST": "1",
            "TEST_TARGET": "//bench:test_suite",
            "TEST_TMPDIR": str(root / "tmp"),
            "XML_OUTPUT_FILE": str(root / "test.xml"),
        }
        args = ["-q", "-p", "no:randomly", "-p", "no:cacheprovider", "test_suite.py"]

        def pytest_run() -> None:
            _python("-m", "pytest", *args, f"--junitxml={root / 'p.xml'}", cwd=root)

        def pytest_bazel_run() -> None:
            _python("-m", "pytest_bazel", *args, cwd=root, **bazel_env)

        # Warm up the file system caches and the byte code.
        pytest_run()
        pytest_bazel_run()
        return _median_ms(pytest_run, repeat), _median_ms(pytest_bazel_run, repeat)


# pytest and what it imports when it is imported.
_PYTEST_MODULES = (
    "pytest",
    "_pytest",
    "pluggy",
    "iniconfig",
    "packaging",
    "pygments",
    "exceptiongroup",
    "tomli",
)


def _copy_sources(modules: tuple[str, ...], dest: Path) -> None:
    """Copy the sources of `modules` to `dest`, without their .pyc files."""
    for name in modules:
        spec = importlib.util.find_spec(name)
        if spec is None or spec.origin is None:
            continue
        if spec.submodule_search_locations:
            shutil.copytree(
                Path(spec.origin).parent,
                dest / name,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        else:
            shutil.copy(spec.origin, dest)


def pyc_import_ms(repeat: int = 7) -> dict[str, tuple[float, float]]:
    """Return the import times of pytest and pytest_bazel without and with .pyc.

    Under `bazel test`, the runfiles have no .pyc files unless rules_python
    compiles them, so every test compiles the sources again.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _copy_sources((*_PYTEST_MODULES, "pytest_bazel"), root)

        def median_ms(code: str) -> float:
            # -B: do not write .pyc files, so that each run compiles again.
            return (
                statistics.median(
                    float(
                        _python(
                            "-B",
                            "-c",
                            f"import sys; sys.path.insert(0, {tmp!r}); {code}",
                        )
                    )
                    for _ in range(repeat)
                )
                * 1000
            )

        pytest_code = (
            "import time; start = time.perf_counter(); import pytest; "
            "print(time.perf_counter() - start)"
        )
        bazel_code = (
            "import time, pytest; start = time.perf_counter(); "
            "import pytest_bazel.main; print(time.perf_counter() - start)"
        )
        without = median_ms(pytest_code), median_ms(bazel_code)
        compileall.compile_dir(tmp, quiet=1)
        with_pyc = median_ms(pytest_code), median_ms(bazel_code)
    return {
        "pytest": (without[0], with_pyc[0]),
        "pytest_bazel": (without[1], with_pyc[1]),
    }


def filter_ms(test_filter: str, ids: list[str], repeat: int = 7) -> float:
    """Return the time that the exact `--test_filter` takes for `ids`."""
    selects = _Filter(test_filter)
    return _median_ms(lambda: [selects(i) for i in ids], repeat)


def shard_ms(ids: list[str], repeat: int = 7) -> float:
    """Return the time that splitting `ids` into shards takes."""
    return _median_ms(lambda: select_shard(ids, 3, 8), repeat)


def results() -> str:
    """Run the benchmarks and return the README block."""
    ids = node_ids(_TESTS)
    plain, bazel = run_overhead_ms()
    pyc = pyc_import_ms()
    rows = [
        (
            "Importing pytest without / with `.pyc` files",
            "{:.0f} ms / {:.0f} ms".format(*pyc["pytest"]),
        ),
        (
            "Importing `pytest_bazel` on top of pytest without / with `.pyc` files",
            "{:.1f} ms / {:.1f} ms".format(*pyc["pytest_bazel"]),
        ),
        (
            f"A run of {_SUITE_TESTS} tests with `pytest --junitxml` / with `pytest_bazel`",
            f"{plain:.0f} ms / {bazel:.0f} ms",
        ),
        (
            f"`PYTEST_BAZEL_EXACT_TEST_FILTER=1` with a name, {_TESTS} tests",
            f"{filter_ms('TestThing4.test_function_5', ids):.1f} ms",
        ),
        (
            f"`PYTEST_BAZEL_EXACT_TEST_FILTER=1` with 4 filters, {_TESTS} tests",
            f"{filter_ms('test_function_1,test_function_2,TestThing1.test_function_3,service2/tests', ids):.1f} ms",
        ),
        (f"Splitting {_TESTS} tests into shards", f"{shard_ms(ids):.1f} ms"),
    ]
    machine = (
        f"Python {platform.python_version()}, pytest {pytest.__version__}, "
        f"{platform.system()} {platform.machine()}, {os.cpu_count()} CPUs"
    )
    return f"{table(rows)}\n\nMedians on {machine}."


def main(argv: Optional[list[str]] = None) -> int:
    """Run the benchmarks, and write them to README.md with `--update`."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--update", action="store_true", help="write the results to README.md"
    )
    args = parser.parse_args(argv)

    block = results()
    print(block)
    if not args.update:
        return 0

    # `bazel run` starts the script in its runfiles, README.md is in the
    # workspace.
    readme = Path(os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")) / "README.md"
    try:
        readme.write_text(replace_block(readme.read_text(), block))
    except ReadmeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"updated {readme}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
