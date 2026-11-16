"""PYTEST_BAZEL_EXACT_TEST_FILTER selects tests by their exact names."""

import pytest

from pytest_bazel._impl.exact_filter import matches
from pytest_bazel._impl.main import BazelEnv, _pytest_args

pytest_plugins = ["pytester"]

_ID = "pkg/test_mod.py::TestCase::test_add[1.5]"


@pytest.mark.parametrize(
    ("test_filter", "want"),
    [
        ("test_add", True),
        ("test_ad", False),
        ("test_add[1.5]", True),
        ("test_add[1]", False),
        ("TestCase", True),
        ("TestCase.test_add", True),
        ("TestCase::test_add", True),
        ("test_mod", True),
        ("test_mod.test_add", True),
        ("pkg.test_mod.TestCase.test_add", True),
        ("test_add.TestCase", False),
        ("test_mod.py", True),
        ("est_mod.py", False),
        ("pkg/test_mod.py::TestCase", True),
        ("test_mod.py::TestCase::test_add", True),
        ("test_mod.py::TestCase::test_ad", False),
        ("other,test_add", True),
        ("pkg/", True),
        ("other/pkg", False),
        ("pk/", False),
    ],
)
def test_matches(test_filter, want):
    assert matches(test_filter, _ID) is want


_TESTS = """
import pytest

class TestMath:
    def test_add(self): pass
    def test_add_many(self): pass

def test_other(): pass

@pytest.mark.parametrize("x", [0.5, 0.25])
def test_param(x): pass
"""


def _selected(pytester, test_filter, flag="1"):
    (pytester.path / "test_mod.py").write_text(_TESTS)
    env = BazelEnv(
        {
            "BAZEL_TEST": "1",
            "TESTBRIDGE_TEST_ONLY": test_filter,
            "PYTEST_BAZEL_EXACT_TEST_FILTER": flag,
        }
    )
    rec = pytester.inline_run("-p", "no:randomly", *_pytest_args(args=[], env=env))
    passed, _, failed = rec.listoutcomes()
    assert not failed
    return sorted(r.nodeid.partition("::")[2] for r in passed)


@pytest.mark.parametrize(
    ("test_filter", "want"),
    [
        ("TestMath.test_add", ["TestMath::test_add"]),
        ("test_param[0.5]", ["test_param[0.5]"]),
        ("TestMath.test_add,test_other", ["TestMath::test_add", "test_other"]),
        # A `-k` expression, as it has spaces.
        (
            "test_add or test_other",
            ["TestMath::test_add", "TestMath::test_add_many", "test_other"],
        ),
    ],
)
def test_selects(pytester, test_filter, want):
    assert _selected(pytester, test_filter) == want


@pytest.mark.parametrize("test_filter", ["pkg/sub", "pkg/sub/", "sub"])
def test_matches_a_directory(test_filter):
    assert matches(test_filter, "pkg/sub/test_x.py::test_a")


def test_k_matches_substrings_without_the_flag(pytester):
    assert _selected(pytester, "TestMath.test_add", flag="0") == [
        "TestMath::test_add",
        "TestMath::test_add_many",
    ]


def test_filter_without_tests_selects_all(pytester):
    assert len(_selected(pytester, ",")) == len(_selected(pytester, ",", flag="0"))


def test_on_by_default():
    env = BazelEnv({"BAZEL_TEST": "1", "TESTBRIDGE_TEST_ONLY": "test_a"})

    assert "pytest_bazel._impl.exact_filter" in _pytest_args(args=[], env=env)


def test_can_be_turned_off():
    env = BazelEnv(
        {
            "BAZEL_TEST": "1",
            "TESTBRIDGE_TEST_ONLY": "test_a",
            "PYTEST_BAZEL_EXACT_TEST_FILTER": "0",
        }
    )

    assert "pytest_bazel._impl.exact_filter" not in _pytest_args(args=[], env=env)


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
