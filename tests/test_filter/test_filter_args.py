import pytest

from pytest_bazel.main import BazelEnv, _pytest_args
from pytest_bazel.main import main as _main

pytest_plugins = ["pytester"]

_TESTS = """
class TestCase:
    def test_a(self): pass
    def test_b(self): pass

class TestOther:
    def test_a(self): pass

def test_a(): pass

import pytest

@pytest.mark.parametrize("x", [0.5, 0.25])
def test_param(x): pass
"""


@pytest.fixture
def _tests(pytester):
    (pytester.path / "pkg").mkdir()
    (pytester.path / "pkg" / "test_mod.py").write_text(_TESTS)
    (pytester.path / "pkg" / "test_unrelated.py").write_text("def test_a(): pass\n")


def _selected(pytester, test_filter, args=()):
    env = BazelEnv({"BAZEL_TEST": "1", "TESTBRIDGE_TEST_ONLY": test_filter})
    rec = pytester.inline_run(*_pytest_args(args=list(args), env=env))
    passed, _, failed = rec.listoutcomes()
    assert not failed
    return sorted(r.nodeid for r in passed)


@pytest.mark.usefixtures("_tests")
@pytest.mark.parametrize(
    ("test_filter", "want"),
    [
        pytest.param(
            "TestCase.test_a", ["pkg/test_mod.py::TestCase::test_a"], id="class.method"
        ),
        pytest.param(
            "TestCase::test_a",
            ["pkg/test_mod.py::TestCase::test_a"],
            id="class::method",
        ),
        pytest.param(
            "TestCase",
            ["pkg/test_mod.py::TestCase::test_a", "pkg/test_mod.py::TestCase::test_b"],
            id="class",
        ),
        pytest.param(
            "test_mod.test_a",
            [
                "pkg/test_mod.py::TestCase::test_a",
                "pkg/test_mod.py::TestOther::test_a",
                "pkg/test_mod.py::test_a",
            ],
            id="module.function",
        ),
        pytest.param(
            "pkg/test_mod.py::TestOther::test_a",
            ["pkg/test_mod.py::TestOther::test_a"],
            id="node_id",
        ),
        pytest.param("test_unrelated.py", ["pkg/test_unrelated.py::test_a"], id="file"),
        pytest.param(
            "TestCase.test_b,TestOther.test_a",
            ["pkg/test_mod.py::TestCase::test_b", "pkg/test_mod.py::TestOther::test_a"],
            id="comma_separated",
        ),
        pytest.param(
            "test_param[0.5]", ["pkg/test_mod.py::test_param[0.5]"], id="dot_in_param"
        ),
        pytest.param(
            "TestCase and not test_b",
            ["pkg/test_mod.py::TestCase::test_a"],
            id="keyword_expression",
        ),
    ],
)
def test_filter_selects(pytester, test_filter, want):
    assert _selected(pytester, test_filter) == want


@pytest.mark.usefixtures("_tests")
def test_filter_with_explicit_paths(pytester):
    """`pytest_test` from rules_python passes the srcs as paths."""
    env = BazelEnv({"BAZEL_TEST": "1", "TESTBRIDGE_TEST_ONLY": "TestCase.test_b"})

    rec = pytester.inline_run(*_pytest_args(args=["pkg/test_mod.py"], env=env))

    passed, _, _ = rec.listoutcomes()
    assert [r.nodeid for r in passed] == ["pkg/test_mod.py::TestCase::test_b"]


@pytest.mark.usefixtures("_tests")
@pytest.mark.parametrize(
    "user_args",
    [["-k", "not TestCase"], ["-knot TestCase"], ["-k=not TestCase"]],
    ids=["separate", "attached", "equals"],
)
def test_filter_is_combined_with_the_k_of_the_user(pytester, user_args):
    """A `-k` in the `args` of the target still applies."""
    assert _selected(pytester, "test_a", user_args) == [
        "pkg/test_mod.py::TestOther::test_a",
        "pkg/test_mod.py::test_a",
        "pkg/test_unrelated.py::test_a",
    ]


@pytest.mark.usefixtures("_tests")
def test_filter_with_an_empty_k_of_the_user(pytester):
    assert _selected(pytester, "TestCase.test_b", ["-k", ""]) == [
        "pkg/test_mod.py::TestCase::test_b"
    ]


def test_says_when_the_filter_selects_nothing(capfd):
    env = BazelEnv({"BAZEL_TEST": "1", "TESTBRIDGE_TEST_ONLY": "test_typo"})

    code = _main(
        args=[], pytest_main=lambda _: pytest.ExitCode.NO_TESTS_COLLECTED, env=env
    )

    assert code == 0
    assert "--test_filter selected no tests (-k 'test_typo')" in capfd.readouterr().err


if __name__ == "__main__":
    from pytest_bazel import main

    main()
