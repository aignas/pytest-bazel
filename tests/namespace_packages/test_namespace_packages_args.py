import pytest

from pytest_bazel.main import BazelEnv, _pytest_args

pytest_plugins = ["pytester"]

_ARG = "consider_namespace_packages=true"


def _args(args=()):
    return _pytest_args(args=list(args), env=BazelEnv({"BAZEL_TEST": "1"}))


@pytest.mark.parametrize(
    ("version", "want"),
    [
        ((7, 4, 0), False),
        ((8, 0, 2), False),
        ((8, 1, 0), True),
        ((9, 1, 1), True),
    ],
)
def test_enabled_from_pytest_8_1(monkeypatch, version, want):
    monkeypatch.setattr(pytest, "version_tuple", version)

    args = _args()

    assert (_ARG in args) is want, args
    if want:
        assert args[args.index(_ARG) - 1] == "-o"


def test_not_enabled_without_version_tuple(monkeypatch):
    monkeypatch.delattr(pytest, "version_tuple")

    assert _ARG not in _args()


@pytest.fixture()
def _bazel_package(pytester, monkeypatch):
    """Create `mypkg/json/test_name.py` where only `json` has an `__init__.py`."""
    pkg = pytester.path / "mypkg" / "json"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").touch()
    (pkg / "test_name.py").write_text(
        "def test_name():\n"
        "    import json\n"
        "    assert __name__ == 'mypkg.json.test_name'\n"
        "    assert hasattr(json, 'dumps'), 'stdlib json must not be shadowed'\n"
    )
    # The runfiles root is on sys.path under bazel.
    monkeypatch.syspath_prepend(pytester.path)


@pytest.mark.skipif(
    pytest.version_tuple < (8, 1), reason="consider_namespace_packages needs pytest 8.1"
)
@pytest.mark.usefixtures("_bazel_package")
def test_module_named_after_bazel_package(pytester):
    rec = pytester.inline_run(*_args())

    rec.assertoutcome(passed=1)


@pytest.mark.skipif(
    pytest.version_tuple < (8, 1), reason="consider_namespace_packages needs pytest 8.1"
)
@pytest.mark.usefixtures("_bazel_package")
def test_user_can_opt_out(pytester):
    rec = pytester.inline_run(*_args(["-o", "consider_namespace_packages=false"]))

    rec.assertoutcome(failed=1)


if __name__ == "__main__":
    from pytest_bazel import main

    main()
