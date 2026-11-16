class TestMath:
    def test_add(self):
        assert 1 + 1 == 2

    def test_add_many(self):
        assert 1 + 1 + 1 == 3

    def test_sub(self):
        assert 2 - 1 == 1


def test_other():
    pass


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
