"""pytest finds no config files above the runfiles root, as in the sandbox.

Without the sandbox, e.g. on Windows, with `--spawn_strategy=local` or under
`bazel run`, the execroot above the runfiles has the files of the workspace.
"""

import pytest

from pytest_bazel._impl.main import BazelEnv, _prepare, _pytest_args

pytest_plugins = ["pytester"]

_TEST = """
def test_x(request, pytestconfig):
    markers = pytestconfig.getini("markers")
    print("NODEID", request.node.nodeid)
    print("MARKERS", [m.split(":")[0] for m in markers if ":" in m])
"""


@pytest.fixture
def runfiles(pytester, monkeypatch):
    """`pytester.path` is the execroot, with the pytest.ini of the workspace."""
    pytester.makeini("[pytest]\nmarkers =\n    workspace: from the workspace\n")
    root = pytester.path / "runfiles"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "test_x.py").write_text(_TEST)
    monkeypatch.chdir(root)
    return root


def _markers(out):
    """Return the names of the markers that the test printed."""
    line = next(line for line in out.splitlines() if "MARKERS" in line)
    return line


def _run(pytester, tmp_path, *args, **env):
    bazel_env = BazelEnv(
        {"BAZEL_TEST": "1", "TEST_TMPDIR": str(tmp_path / "tmp"), **env}
    )
    _prepare(bazel_env)
    result = pytester.runpytest(
        "-p", "no:randomly", "-s", *_pytest_args(args=list(args), env=bazel_env)
    )
    assert result.ret == pytest.ExitCode.OK, result.stdout.str()
    return result.stdout.str()


def test_no_config_in_the_runfiles(pytester, tmp_path, runfiles):
    out = _run(pytester, tmp_path)

    assert "NODEID pkg/test_x.py::test_x" in out
    assert "'workspace'" not in _markers(out)


def test_bazel_run(pytester, tmp_path, runfiles):
    out = _run(pytester, tmp_path, BUILD_WORKSPACE_DIRECTORY=str(pytester.path))

    assert "NODEID pkg/test_x.py::test_x" in out


def test_config_in_the_runfiles_root(pytester, tmp_path, runfiles):
    (runfiles / "pytest.ini").write_text("[pytest]\nmarkers =\n    inner: x\n")

    out = _run(pytester, tmp_path)

    assert "NODEID pkg/test_x.py::test_x" in out
    assert "'inner'" in _markers(out)


def test_config_next_to_the_path_args(pytester, tmp_path, runfiles):
    """As in the sandbox, the config next to the paths sets the rootdir."""
    (runfiles / "pkg" / "pytest.ini").write_text("[pytest]\nmarkers =\n    pkg: x\n")

    out = _run(pytester, tmp_path, "pkg/test_x.py")

    assert "NODEID test_x.py::test_x" in out
    assert "'pkg'" in _markers(out)


def test_user_config_wins(pytester, tmp_path, runfiles):
    (runfiles / "my.ini").write_text("[pytest]\nmarkers =\n    mine: x\n")

    out = _run(pytester, tmp_path, "-c", "my.ini")

    assert "'mine'" in _markers(out)
    assert "'workspace'" not in _markers(out)


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
