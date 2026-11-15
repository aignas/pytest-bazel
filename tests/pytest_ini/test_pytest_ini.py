from pathlib import Path


def test_pytest_ini_is_used(pytestconfig, request):
    # The test ids stay relative to the runfiles root.
    assert request.node.nodeid.startswith("tests/pytest_ini/")
    assert pytestconfig.inipath is not None, "no ini file found"
    assert Path(pytestconfig.inipath).parent.name == "pytest_ini"
    assert any(m.startswith("from_pytest_ini") for m in pytestconfig.getini("markers"))


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
