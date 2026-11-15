def test_passes(tmp_path):
    (tmp_path / "passed.txt").write_text("not kept")


def test_fails(tmp_path):
    out = tmp_path / "failed.txt"
    out.write_text("kept for debugging")
    assert out.read_text() == "something else"


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
