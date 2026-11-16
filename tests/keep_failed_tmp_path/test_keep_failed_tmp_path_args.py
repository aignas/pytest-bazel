import pytest

from pytest_bazel._impl.main import BazelEnv, _pytest_args

pytest_plugins = ["pytester"]

_FLAG = "PYTEST_BAZEL_KEEP_FAILED_TMP_PATH"
_TESTS = """
def test_ok(tmp_path):
    (tmp_path / "ok.txt").write_text("ok")

def test_bad(tmp_path):
    (tmp_path / "bad.txt").write_text("bad")
    assert False
"""


def _env(tmp_path, *, flag="1"):
    env = {
        "BAZEL_TEST": "1",
        "TEST_TMPDIR": str(tmp_path / "tmp"),
        "TEST_UNDECLARED_OUTPUTS_DIR": str(tmp_path / "outputs"),
    }
    if flag is not None:
        env[_FLAG] = flag
    return BazelEnv(env)


def _basetemp(args):
    return next(a for a in args if a.startswith("--basetemp="))


def test_args(tmp_path):
    args = _pytest_args(args=[], env=_env(tmp_path))

    assert _basetemp(args) == f"--basetemp={tmp_path / 'outputs' / 'pytest'}"
    i = args.index("tmp_path_retention_policy=failed")
    assert args[i - 1] == "-o"


@pytest.mark.parametrize("flag", [None, "0"], ids=["unset", "0"])
def test_off_by_default(tmp_path, flag):
    args = _pytest_args(args=[], env=_env(tmp_path, flag=flag))

    assert _basetemp(args) == f"--basetemp={tmp_path / 'tmp' / 'pytest'}"
    assert "tmp_path_retention_policy=failed" not in args


def test_needs_pytest_7_3(tmp_path, monkeypatch):
    monkeypatch.setattr(pytest, "version_tuple", (7, 2, 0))

    args = _pytest_args(args=[], env=_env(tmp_path))

    assert _basetemp(args) == f"--basetemp={tmp_path / 'tmp' / 'pytest'}"


def test_only_failed_tmp_paths_are_kept(pytester, tmp_path):
    pytester.makepyfile(test_mod=_TESTS)
    outputs = tmp_path / "outputs"
    outputs.mkdir()

    rec = pytester.inline_run(*_pytest_args(args=[], env=_env(tmp_path)))

    rec.assertoutcome(passed=1, failed=1)
    kept = sorted(p.name for p in outputs.rglob("*.txt"))
    assert kept == ["bad.txt"]


if __name__ == "__main__":
    from pytest_bazel import main

    main()
