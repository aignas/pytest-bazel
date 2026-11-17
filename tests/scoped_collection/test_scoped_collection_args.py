import pytest

from pytest_bazel._impl.main import BazelEnv, _pytest_args

pytest_plugins = ["pytester"]


def _env(target=None, *, opt_in=True):
    env = {"BAZEL_TEST": "1"}
    if target:
        env["TEST_TARGET"] = target
    if opt_in:
        env["PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE"] = "1"
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


@pytest.fixture
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
@pytest.mark.parametrize(
    "target",
    [
        pytest.param("//a:test", id="single"),
        pytest.param("//a:t_py3.11_test", id="python_versions"),
    ],
)
@pytest.mark.parametrize(
    ("srcs", "want"),
    [
        pytest.param(["a/test_a.py"], ["a/test_a.py::test_ok"], id="own_package"),
        pytest.param(["b/test_b.py"], ["b/test_b.py::test_ok"], id="other_package"),
    ],
)
def test_rules_python_pytest_test(pytester, target, srcs, want):
    """`pytest_test` from rules_python 2.5+ appends the `srcs` to the args.

    Its bootstrap calls `pytest_bazel.main(sys.argv[1:] + srcs)`, so the srcs
    must be collected as they are, whatever package the target is in.
    """
    user_args = ["-v"]

    rec = pytester.inline_run(*_pytest_args(args=user_args + srcs, env=_env(target)))

    assert _passed(rec) == want


@pytest.mark.usefixtures("_two_packages")
def test_collects_everything_without_target(pytester):
    rec = pytester.inline_run(*_pytest_args(args=[], env=_env()))

    assert _passed(rec) == ["a/test_a.py::test_ok", "b/test_b.py::test_ok"]


@pytest.mark.usefixtures("_two_packages")
@pytest.mark.parametrize("value", [None, "0"], ids=["unset", "0"])
def test_off_by_default(pytester, value):
    env = _env("//a:test", opt_in=False)
    if value is not None:
        env.env["PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE"] = value

    args = _pytest_args(args=[], env=env)
    rec = pytester.inline_run(*args)

    assert _testpaths(args) == []
    assert _passed(rec) == ["a/test_a.py::test_ok", "b/test_b.py::test_ok"]


@pytest.mark.parametrize("value", ["true", "yes", "", "2"])
def test_flag_must_be_0_or_1(value):
    env = _env("//a:test", opt_in=False)
    env.env["PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE"] = value

    with pytest.raises(ValueError, match="must be 0 or 1"):
        _pytest_args(args=[], env=env)


if __name__ == "__main__":
    from pytest_bazel import main

    main()
