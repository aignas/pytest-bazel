from pytest_bazel.annotations import summary
from pytest_bazel.main import BazelEnv, _pytest_args

pytest_plugins = ["pytester"]

_TESTS = """
import pytest

def test_ok(): pass
def test_bad(): assert False
@pytest.mark.skip
def test_skipped(): pass
@pytest.fixture
def broken(): raise RuntimeError
def test_error(broken): pass
"""


def _run(pytester, tmp_path):
    annotations = tmp_path / "annotations"
    annotations.mkdir()
    env = BazelEnv(
        {"BAZEL_TEST": "1", "TEST_UNDECLARED_OUTPUTS_ANNOTATIONS_DIR": str(annotations)}
    )
    pytester.inline_run(*_pytest_args(args=[], env=env))
    return annotations / "pytest_bazel.part"


def test_annotation(pytester, tmp_path):
    pytester.makepyfile(test_mod=_TESTS)

    part = _run(pytester, tmp_path)

    assert part.read_text().splitlines() == [
        "pytest: 1 failed, 1 error, 1 passed, 1 skipped",
        "FAILED test_mod.py::test_bad",
        "ERROR test_mod.py::test_error",
    ]


def test_annotation_without_tests(pytester, tmp_path):
    pytester.makepyfile(test_mod="")

    assert _run(pytester, tmp_path).read_text() == "pytest: no tests ran\n"


def test_not_loaded_without_the_dir():
    args = _pytest_args(args=[], env=BazelEnv({"BAZEL_TEST": "1"}))

    assert "pytest_bazel.annotations" not in args


class _Report:
    def __init__(self, nodeid):
        self.nodeid = nodeid


def test_failures_are_capped():
    stats = {"failed": [_Report(f"t.py::test_{i}") for i in range(25)]}

    lines = summary(stats).splitlines()

    assert lines[0] == "pytest: 25 failed"
    assert len(lines) == 1 + 20 + 1
    assert lines[-1] == "... and 5 more, see the test log"


if __name__ == "__main__":
    from pytest_bazel import main

    main()
