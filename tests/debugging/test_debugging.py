import sys

import pytest

from pytest_bazel._impl.main import BazelEnv, _pytest_args

pytest_plugins = ["pytester"]


def _args(*args):
    return _pytest_args(args=list(args), env=BazelEnv({"BAZEL_TEST": "1"}))


@pytest.fixture(autouse=True)
def _target(monkeypatch):
    monkeypatch.setenv("TEST_TARGET", "//pkg:my_test")


def test_loaded_under_bazel_test():
    assert "pytest_bazel._impl.debugging" in _args()


@pytest.mark.parametrize(
    "environ",
    [
        # `bazel run` of a test target sets the test env, BAZEL_TEST too.
        pytest.param(
            {"BAZEL_TEST": "1", "BUILD_WORKSPACE_DIRECTORY": "/ws"}, id="bazel_run"
        ),
        pytest.param({}, id="without_bazel"),
    ],
)
def test_not_loaded_with_a_terminal(environ):
    args = _pytest_args(args=["--pdb"], env=BazelEnv(environ))

    assert "pytest_bazel._impl.debugging" not in args


@pytest.mark.parametrize("flag", ["--pdb", "--trace"])
def test_debugger_flags_fail(pytester, flag):
    pytester.makepyfile("def test_ok(): pass")

    result = pytester.runpytest(*_args(flag))

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(
        [f"*{flag} needs a terminal*`bazel run //pkg:my_test -- --pdb`*"]
    )


def test_debugger_flags_from_addopts_fail(pytester):
    pytester.makeini("[pytest]\naddopts = --pdb\n")
    pytester.makepyfile("def test_ok(): pass")

    result = pytester.runpytest(*_args())

    assert result.ret == pytest.ExitCode.USAGE_ERROR


def test_breakpoint_fails(pytester):
    pytester.makepyfile("def test_debug():\n    breakpoint()\n")

    result = pytester.runpytest(*_args())

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            ">       breakpoint()",
            "E       RuntimeError: breakpoint() was called*bazel run //pkg:my_test*",
        ]
    )
    assert "debugging.py" not in result.stdout.str()


def test_pythonbreakpoint_is_respected(pytester, monkeypatch):
    monkeypatch.setenv("PYTHONBREAKPOINT", "0")
    pytester.makepyfile("def test_debug():\n    breakpoint()\n")

    # In a subprocess, as this test runs with the hook of this plugin.
    result = pytester.runpytest_subprocess(*_args())

    result.assert_outcomes(passed=1)


def test_pythonbreakpoint_is_ignored_with_isolated_python(pytester, monkeypatch):
    monkeypatch.setenv("PYTHONBREAKPOINT", "0")
    pytester.makepyfile("def test_debug():\n    breakpoint()\n")

    result = pytester.run(sys.executable, "-I", "-m", "pytest", *_args())

    assert result.ret == pytest.ExitCode.TESTS_FAILED, result.stdout.str()
    result.stdout.fnmatch_lines(["*RuntimeError: breakpoint() was called*"])


def test_breakpointhook_is_restored(pytester):
    hook = sys.breakpointhook
    pytester.makepyfile("def test_ok(): pass")

    pytester.inline_run(*_args())

    assert sys.breakpointhook is hook


if __name__ == "__main__":
    from pytest_bazel import main

    main()
