"""The warnings of the tests are written to TEST_WARNINGS_OUTPUT_FILE."""

import pytest

from pytest_bazel._impl.main import BazelEnv, _pytest_args
from pytest_bazel._impl.main import main as _main

pytest_plugins = ["pytester"]

_TEST = """
import warnings

def test_warns():
    warnings.warn("from the test", DeprecationWarning)
"""


def test_writes_the_warnings_of_the_tests(pytester, tmp_path):
    out = tmp_path / "test.warnings"
    pytester.makepyfile(_TEST)
    env = BazelEnv({"BAZEL_TEST": "1", "TEST_WARNINGS_OUTPUT_FILE": str(out)})

    result = pytester.runpytest(*_pytest_args(args=[], env=env))

    assert result.ret == pytest.ExitCode.OK
    assert "DeprecationWarning: from the test" in out.read_text()


def test_keeps_the_warnings_of_the_tests_with_later_warnings(pytester, tmp_path):
    """`main` writes the warnings outside of pytest to the same file."""
    out = tmp_path / "test.warnings"
    pytester.makepyfile(_TEST)
    pytester.makeconftest(
        "import warnings\n"
        "def pytest_unconfigure(config):\n"
        "    warnings.warn('late', UserWarning)\n"
    )
    env = BazelEnv({"BAZEL_TEST": "1", "TEST_WARNINGS_OUTPUT_FILE": str(out)})

    _main(args=[], pytest_main=lambda args: pytester.inline_run(*args).ret, env=env)

    text = out.read_text()
    assert "DeprecationWarning: from the test" in text, text
    assert "UserWarning: late" in text, text


def test_writes_warnings_the_locale_cannot_encode(pytester, tmp_path, monkeypatch):
    """E.g. on Windows, where the locale encoding is often cp1252."""
    for var, value in {
        "LC_ALL": "C",
        "PYTHONUTF8": "0",
        "PYTHONCOERCECLOCALE": "0",
    }.items():
        monkeypatch.setenv(var, value)
    out = tmp_path / "test.warnings"
    pytester.makepyfile(
        "import warnings\n"
        "def test_warns():\n"
        "    warnings.warn('caf\\u00e9 \\u2603', UserWarning)\n"
    )
    env = BazelEnv({"BAZEL_TEST": "1", "TEST_WARNINGS_OUTPUT_FILE": str(out)})

    result = pytester.runpytest_subprocess(*_pytest_args(args=[], env=env))

    assert result.ret == pytest.ExitCode.OK, result.stdout.str()
    assert "caf\u00e9 \u2603" in out.read_text(encoding="utf-8")


def test_not_loaded_without_the_file():
    args = _pytest_args(args=[], env=BazelEnv({"BAZEL_TEST": "1"}))

    assert "pytest_bazel._impl.warnings_output" not in args


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
