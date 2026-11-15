"""Tests of another bazel package that end up in the runfiles via `deps`."""

import pytest


def test_must_not_be_collected():
    pytest.fail(
        "tests from //tests/scoped_collection_dep must not run in //tests/scoped_collection"
    )
