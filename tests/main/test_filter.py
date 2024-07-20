import pytest

from pytest_bazel.main import BazelEnv


@pytest.mark.parametrize(
    ("filter", "want"),
    [
        ("foo.py", "foo.py"),
        ("test_foo", "test_foo"),
        ("TestClass.fn", "TestClass::fn"),
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
