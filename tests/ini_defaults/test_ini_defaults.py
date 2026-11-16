"""The `-o` defaults of pytest_bazel do not override the config file of the user."""

import xml.etree.ElementTree as ET

import pytest

from pytest_bazel.main import BazelEnv, _pytest_args

pytest_plugins = ["pytester"]

_SUITE = "junit_suite_name=//pkg:test"


def _env(tmp_path, **extra):
    return BazelEnv(
        {
            "BAZEL_TEST": "1",
            "TEST_TARGET": "//pkg:test",
            "XML_OUTPUT_FILE": str(tmp_path / "test.xml"),
            **extra,
        }
    )


def test_default_without_config(pytester, tmp_path):
    assert _SUITE in _pytest_args(args=[], env=_env(tmp_path))


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("pytest.ini", "[pytest]\njunit_suite_name = mine\n"),
        ("tox.ini", "[pytest]\njunit_suite_name = mine\n"),
        ("setup.cfg", "[tool:pytest]\njunit_suite_name = mine\n"),
        ("pyproject.toml", '[tool.pytest.ini_options]\njunit_suite_name = "mine"\n'),
    ],
)
def test_config_file_wins(pytester, tmp_path, name, text):
    (pytester.path / name).write_text(text)

    assert _SUITE not in _pytest_args(args=[], env=_env(tmp_path))


def test_other_sections_do_not_count(pytester, tmp_path):
    (pytester.path / "tox.ini").write_text("[tox]\njunit_suite_name = mine\n")

    assert _SUITE in _pytest_args(args=[], env=_env(tmp_path))


def test_config_next_to_the_path_args(pytester, tmp_path):
    (pytester.path / "pkg").mkdir()
    (pytester.path / "pkg" / "pytest.ini").write_text(
        "[pytest]\njunit_suite_name = mine\n"
    )
    (pytester.path / "pkg" / "test_a.py").write_text("def test_a(): pass\n")

    args = _pytest_args(args=["pkg/test_a.py"], env=_env(tmp_path))

    assert _SUITE not in args


@pytest.mark.parametrize(
    "config_args",
    [["-c", "my.ini"], ["-cmy.ini"], ["--config-file=my.ini"]],
    ids=["separate", "attached", "equals"],
)
def test_config_of_the_user(pytester, tmp_path, config_args):
    (pytester.path / "pytest.ini").write_text("[pytest]\n")
    (pytester.path / "my.ini").write_text("[pytest]\njunit_suite_name = mine\n")

    assert _SUITE not in _pytest_args(args=config_args, env=_env(tmp_path))


def test_config_from_package(pytester, tmp_path):
    (pytester.path / "pkg").mkdir()
    (pytester.path / "pkg" / "pytest.ini").write_text("[pytest]\ntestpaths = pkg\n")
    env = _env(
        tmp_path,
        PYTEST_BAZEL_CONFIG_FROM_PACKAGE="1",
        PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE="1",
    )

    args = _pytest_args(args=[], env=env)

    assert "testpaths=pkg" not in args
    assert _SUITE in args


def test_opt_in_defaults_defer_to_the_config(pytester, tmp_path):
    (pytester.path / "pytest.ini").write_text("[pytest]\njunit_logging = system-out\n")
    env = _env(tmp_path, PYTEST_BAZEL_JUNIT_OUTPUT="1")

    args = _pytest_args(args=[], env=env)

    assert "junit_logging=all" not in args
    assert "junit_log_passing_tests=false" in args


def test_unreadable_config_keeps_the_defaults(pytester, tmp_path):
    (pytester.path / "pyproject.toml").write_text("[tool.pytest\n")

    assert _SUITE in _pytest_args(args=[], env=_env(tmp_path))


def test_suite_name_of_the_user_in_the_report(pytester, tmp_path):
    pytester.makeini("[pytest]\njunit_suite_name = mine\n")
    pytester.makepyfile("def test_ok(): pass\n")

    pytester.runpytest(*_pytest_args(args=[], env=_env(tmp_path)))

    suite = ET.parse(tmp_path / "test.xml").getroot().find("testsuite")
    assert suite is not None
    assert suite.get("name") == "mine"


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
