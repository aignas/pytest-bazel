import xml.etree.ElementTree as ET

import pytest

from pytest_bazel._impl.main import BazelEnv, _pytest_args

pytest_plugins = ["pytester"]

_FLAG = "PYTEST_BAZEL_JUNIT_OUTPUT"
_TESTS = """
import logging
import sys

def test_passes():
    print("stdout of a passing test")

def test_fails():
    print("stdout of a failing test")
    print("stderr of a failing test", file=sys.stderr)
    logging.getLogger(__name__).warning("log of a failing test")
    assert False
"""


def _env(xml_file, *, flag="1"):
    env = {"BAZEL_TEST": "1", "XML_OUTPUT_FILE": str(xml_file)}
    if flag is not None:
        env[_FLAG] = flag
    return BazelEnv(env)


def _output(xml_file):
    """Return the output in the XML for each test case."""
    root = ET.parse(xml_file).getroot()
    return {
        case.get("name"): " ".join(
            e.text or "" for e in case if e.tag in ("system-out", "system-err")
        )
        for case in root.iter("testcase")
    }


def _run(pytester, args=(), **kwargs):
    pytester.makepyfile(test_mod=_TESTS)
    xml_file = pytester.path / "test.xml"
    pytester.inline_run(*_pytest_args(args=list(args), env=_env(xml_file, **kwargs)))
    return _output(xml_file)


def test_output_of_failed_tests(pytester):
    output = _run(pytester)

    assert "stdout of a failing test" in output["test_fails"]
    assert "stderr of a failing test" in output["test_fails"]
    assert "log of a failing test" in output["test_fails"]
    assert output["test_passes"] == "", "passing tests are left out"


@pytest.mark.parametrize("flag", [None, "0"], ids=["unset", "0"])
def test_off_by_default(pytester, flag):
    output = _run(pytester, flag=flag)

    assert output == {"test_passes": "", "test_fails": ""}


def test_user_args_win(pytester):
    output = _run(pytester, args=["-o", "junit_log_passing_tests=true"])

    assert "stdout of a passing test" in output["test_passes"]


def test_without_xml_output():
    args = _pytest_args(args=[], env=BazelEnv({"BAZEL_TEST": "1", _FLAG: "1"}))

    assert "junit_logging=all" not in args


if __name__ == "__main__":
    from pytest_bazel import main

    main()
