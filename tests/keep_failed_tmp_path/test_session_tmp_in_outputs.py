"""Run under bazel test, which validates the outputs that the test leaves."""

import pytest


@pytest.fixture(scope="session")
def shared(tmp_path_factory):
    path = tmp_path_factory.mktemp("shared")
    (path / "data.txt").write_text("for all tests")
    return path


def test_uses_session_tmp(shared, tmp_path):
    (tmp_path / "copy.txt").write_text((shared / "data.txt").read_text())


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
