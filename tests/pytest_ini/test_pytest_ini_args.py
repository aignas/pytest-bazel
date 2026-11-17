import pytest

from pytest_bazel._impl.config import _find_package_config
from pytest_bazel._impl.main import BazelEnv, _pytest_args

pytest_plugins = ["pytester"]

_FLAG = "PYTEST_BAZEL_CONFIG_FROM_PACKAGE"
_INI = "[pytest]\nmarkers =\n    from_package: in the package config\n"


def _env(target="//a/b:test", *, flag="1"):
    env = {"BAZEL_TEST": "1", "TEST_TARGET": target}
    if flag is not None:
        env[_FLAG] = flag
    return BazelEnv(env)


@pytest.fixture
def runfiles(tmp_path, monkeypatch):
    (tmp_path / "a" / "b").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.mark.parametrize(
    ("files", "want"),
    [
        pytest.param({"a/b/pytest.ini": ""}, "a/b/pytest.ini", id="pytest.ini"),
        pytest.param({"a/b/.pytest.ini": ""}, "a/b/.pytest.ini", id=".pytest.ini"),
        pytest.param({"a/pytest.ini": ""}, "a/pytest.ini", id="parent"),
        pytest.param(
            {"a/b/pyproject.toml": "[tool.pytest.ini_options]\n"},
            "a/b/pyproject.toml",
            id="pyproject.toml",
        ),
        pytest.param({"a/b/tox.ini": "[pytest]\n"}, "a/b/tox.ini", id="tox.ini"),
        pytest.param(
            {"a/b/setup.cfg": "[tool:pytest]\n"}, "a/b/setup.cfg", id="setup.cfg"
        ),
        pytest.param(
            {"a/b/pyproject.toml": "[tool.ruff]\n", "a/pytest.ini": ""},
            "a/pytest.ini",
            id="skip_files_without_pytest_section",
        ),
        pytest.param(
            {"a/b/pyproject.toml": "[tool.pytest.ini_options]\n", "a/b/pytest.ini": ""},
            "a/b/pytest.ini",
            id="pytest_order",
        ),
        pytest.param({"pytest.ini": ""}, None, id="runfiles_root_is_skipped"),
        pytest.param({}, None, id="none"),
    ],
)
def test_find_package_config(runfiles, files, want):
    for name, content in files.items():
        (runfiles / name).write_text(content)

    got = _find_package_config("a/b")

    assert (str(got) if got else None) == want


def test_args(runfiles):
    (runfiles / "a" / "b" / "pytest.ini").write_text(_INI)

    args = _pytest_args(args=[], env=_env())

    i = args.index("-c")
    assert args[i : i + 4] == ["-c", "a/b/pytest.ini", "--rootdir=.", "--confcutdir=."]


@pytest.mark.parametrize("flag", [None, "0"], ids=["unset", "0"])
def test_off_by_default(runfiles, flag):
    (runfiles / "a" / "b" / "pytest.ini").write_text(_INI)

    assert "-c" not in _pytest_args(args=[], env=_env(flag=flag))


@pytest.mark.parametrize("target", ["@other//a/b:test", "//:test"])
def test_only_for_main_repo_packages(runfiles, target):
    (runfiles / "a" / "b" / "pytest.ini").write_text(_INI)

    assert "-c" not in _pytest_args(args=[], env=_env(target))


@pytest.fixture
def _package_with_config(pytester):
    pkg = pytester.path / "a" / "b"
    pkg.mkdir(parents=True)
    (pkg / "pytest.ini").write_text(_INI)
    (pkg / "test_x.py").write_text(
        "def test_x(pytestconfig, request):\n"
        "    assert request.node.nodeid == 'a/b/test_x.py::test_x'\n"
        "    assert any(m.startswith('from_package') for m in pytestconfig.getini('markers'))\n"
    )


@pytest.mark.usefixtures("_package_with_config")
def test_package_config_is_used(pytester):
    rec = pytester.inline_run(*_pytest_args(args=[], env=_env()))

    rec.assertoutcome(passed=1)


@pytest.mark.usefixtures("_package_with_config")
def test_user_config_wins(pytester):
    (pytester.path / "other.ini").write_text("[pytest]\n")

    rec = pytester.inline_run(*_pytest_args(args=["-c", "other.ini"], env=_env()))

    rec.assertoutcome(failed=1)


@pytest.mark.parametrize("conftest_dir", [".", "a"], ids=["runfiles_root", "parent"])
def test_conftest_files_above_the_config_are_loaded(pytester, conftest_dir):
    """`-c` alone would only load the conftest.py files next to and below it."""
    (pytester.path / "a" / "b").mkdir(parents=True)
    (pytester.path / "a" / "b" / "pytest.ini").write_text(_INI)
    (pytester.path / conftest_dir / "conftest.py").write_text(
        "import pytest\n\n@pytest.fixture\ndef from_above():\n    return 1\n"
    )
    (pytester.path / "a" / "b" / "test_x.py").write_text(
        "def test_x(from_above):\n    assert from_above == 1\n"
    )

    rec = pytester.inline_run(*_pytest_args(args=[], env=_env()))

    rec.assertoutcome(passed=1)


if __name__ == "__main__":
    from pytest_bazel import main

    main()
