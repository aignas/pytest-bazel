import time

import pytest


@pytest.mark.parametrize("n", range(4))
def test_slow(n):
    time.sleep(0.5)


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
