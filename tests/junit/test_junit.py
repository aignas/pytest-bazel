import xml.etree.ElementTree as ET

import pytest

from pytest_bazel.main import BazelEnv, _pytest_args

pytest_plugins = ["pytester"]


def _env(**kwargs):
    return BazelEnv({"BAZEL_TEST": "1", **kwargs})


def _suite_names(xml_file):
    root = ET.parse(xml_file).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    return [s.get("name") for s in suites]


def test_suite_name_is_the_target():
    args = _pytest_args(
        args=[],
        env=_env(XML_OUTPUT_FILE="/out/test.xml", TEST_TARGET="//foo:bar_test"),
    )

    assert "--junitxml=/out/test.xml" in args
    i = args.index("junit_suite_name=//foo:bar_test")
    assert args[i - 1] == "-o"


@pytest.mark.parametrize(
    "env",
    [
        pytest.param({"TEST_TARGET": "//foo:bar_test"}, id="no_xml_output"),
        pytest.param({"XML_OUTPUT_FILE": "/out/test.xml"}, id="no_target"),
    ],
)
def test_suite_name_is_not_set(env):
    args = _pytest_args(args=[], env=_env(**env))

    assert not any(a.startswith("junit_suite_name=") for a in args), args


def test_suite_name_in_report(pytester):
    pytester.makepyfile("def test_ok(): pass")
    xml_file = pytester.path / "out" / "test.xml"

    args = _pytest_args(
        args=[],
        env=_env(XML_OUTPUT_FILE=str(xml_file), TEST_TARGET="//foo:bar_test"),
    )
    rec = pytester.inline_run(*args)

    assert rec.ret == pytest.ExitCode.OK
    assert _suite_names(xml_file) == ["//foo:bar_test"]


def test_user_can_override_suite_name(pytester):
    pytester.makepyfile("def test_ok(): pass")
    xml_file = pytester.path / "out" / "test.xml"

    args = _pytest_args(
        args=["-o", "junit_suite_name=custom"],
        env=_env(XML_OUTPUT_FILE=str(xml_file), TEST_TARGET="//foo:bar_test"),
    )
    rec = pytester.inline_run(*args)

    assert rec.ret == pytest.ExitCode.OK
    assert _suite_names(xml_file) == ["custom"]


if __name__ == "__main__":
    from pytest_bazel import main

    main()
