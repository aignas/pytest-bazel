import pytest

from pytest_bazel.main import BazelEnv, _pytest_args

pytest_plugins = ["pytester"]


def _env(target=None):
    env = {"BAZEL_TEST": "1"}
    if target:
        env["TEST_TARGET"] = target
    return BazelEnv(env)


def _testpaths(args):
    return [a for a in args if a.startswith("testpaths=")]


@pytest.mark.parametrize(
    ("target", "want"),
    [
        ("//foo/bar:baz_test", "foo/bar"),
        ("@//foo/bar:baz_test", "foo/bar"),
        ("@@//foo/bar:baz_test", "foo/bar"),
        ("//:baz_test", None),
        ("@other//foo:baz_test", None),
        ("@@other+//foo:baz_test", None),
        (None, None),
    ],
)
def test_package(target, want):
    assert _env(target).test_package == want


def test_testpaths_is_the_package(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "foo" / "bar").mkdir(parents=True)

    args = _pytest_args(args=[], env=_env("//foo/bar:baz_test"))

    assert _testpaths(args) == ["testpaths=foo/bar"]
    assert args[args.index("testpaths=foo/bar") - 1] == "-o"


@pytest.mark.parametrize(
    "target",
    [
        pytest.param("//missing:baz_test", id="missing_dir"),
        pytest.param("//:baz_test", id="root_package"),
        pytest.param("@other//foo:baz_test", id="external_repo"),
        pytest.param(None, id="no_target"),
    ],
)
def test_testpaths_is_not_set(tmp_path, monkeypatch, target):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "foo").mkdir()

    assert _testpaths(_pytest_args(args=[], env=_env(target))) == []


@pytest.fixture()
def _two_packages(pytester):
    for pkg in ("a", "b"):
        (pytester.path / pkg).mkdir()
        (pytester.path / pkg / f"test_{pkg}.py").write_text("def test_ok(): pass\n")


def _passed(rec):
    passed, _, _ = rec.listoutcomes()
    return sorted(r.nodeid for r in passed)


@pytest.mark.usefixtures("_two_packages")
def test_collects_only_the_target_package(pytester):
    rec = pytester.inline_run(*_pytest_args(args=[], env=_env("//a:test")))

    assert _passed(rec) == ["a/test_a.py::test_ok"]


@pytest.mark.usefixtures("_two_packages")
def test_explicit_paths_take_precedence(pytester):
    rec = pytester.inline_run(*_pytest_args(args=["b"], env=_env("//a:test")))

    assert _passed(rec) == ["b/test_b.py::test_ok"]


@pytest.mark.usefixtures("_two_packages")
def test_collects_everything_without_target(pytester):
    rec = pytester.inline_run(*_pytest_args(args=[], env=_env()))

    assert _passed(rec) == ["a/test_a.py::test_ok", "b/test_b.py::test_ok"]


if __name__ == "__main__":
    from pytest_bazel import main

    main()
