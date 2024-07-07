from random import random

import pytest_bazel


def test_random():
    got = random()

    # NOTE @aignas 2024-07-07: this is deterministic on my machine. For now I think I am gong to keep it, as we
    # just want to check that it works. The main unit test is in the `./test_pytest_base.py` file which checks
    # that args are passed through.
    allowed_values = [
        0.13436424411240122,
        0.9560342718892494,
    ]

    assert got in allowed_values


if __name__ == "__main__":
    pytest_bazel.main()
