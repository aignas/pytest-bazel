import pytest

from pytest_bazel.main import BazelEnv


@pytest.mark.parametrize(
    ("filter", "want"),
    [
        ("", ""),
        ("foo.py", "foo.py"),
        ("test_foo", "test_foo"),
        ("TestClass.fn", "TestClass and fn"),
        ("TestClass::fn", "TestClass and fn"),
        ("test_mod.test_fn", "test_mod and test_fn"),
        ("dir/test_mod.py", "test_mod.py"),
        ("dir/test_mod.py::TestClass::fn", "test_mod.py and TestClass and fn"),
        ("test_fn[1]", "test_fn[1]"),
        ("foo or bar", "foo or bar"),
    ],
)
def test_filter(filter: str, want: str):
    env = BazelEnv(
        {
            "TESTBRIDGE_TEST_ONLY": filter,
        }
    )
    assert env.test_filter == want


if __name__ == "__main__":
    from pytest_bazel import main

    main()
