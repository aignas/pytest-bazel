"""A first-party `numpy` package in a bazel package without `__init__.py`.

Without `consider_namespace_packages`, pytest stops walking up at the first
directory without `__init__.py` and imports this file as `numpy.test_...`.
That registers this directory as `numpy` in `sys.modules`, which shadows the
real `numpy` for the code under test.
"""

import sys

import numpy as np


def test_module_name_includes_the_bazel_package():
    assert __name__ == "tests.namespace_packages.numpy.test_not_shadowed"


def test_third_party_package_is_not_shadowed():
    assert np.__file__ != sys.modules[__name__.rpartition(".")[0]].__file__
    assert np.array([1, 2]).sum() == 3  # noqa: PLR2004
