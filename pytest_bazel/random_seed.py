"""Seed the random order and data of the tests from TEST_RANDOM_SEED.

`pytest_bazel.main` loads this plugin when bazel sets TEST_RANDOM_SEED, or
TEST_RUN_NUMBER for `--runs_per_test`. pytest-randomly may be installed but
not loaded, e.g. with `-p no:randomly`, so its `--randomly-seed` flag cannot
be passed on the command line.
"""

import random

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add the option for the seed."""
    group = parser.getgroup("bazel", "Bazel integration")
    group.addoption(
        "--bazel-random-seed",
        type=int,
        metavar="SEED",
        help="Seed for pytest-randomly or `random`, from TEST_RANDOM_SEED.",
    )


# tryfirst: pytest-randomly reads its seed in its own pytest_configure.
@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Pass the seed to pytest-randomly if it is loaded, else seed `random`."""
    seed = config.getoption("bazel_random_seed")
    if seed is None:
        return

    # Check for the option rather than the plugin, as pytest-randomly is
    # named `randomly` when autoloaded and `pytest_randomly` with
    # `-p pytest_randomly`.
    randomly_seed = getattr(config.option, "randomly_seed", None)
    if randomly_seed is None:
        random.seed(seed)
    elif randomly_seed == "default":
        # An explicit `--randomly-seed` of the user wins.
        config.option.randomly_seed = seed
