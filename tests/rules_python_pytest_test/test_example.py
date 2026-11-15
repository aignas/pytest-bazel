import os


def test_runs_through_pytest_bazel():
    # Only set by `pytest_bazel` when it passes `--junitxml`.
    assert os.environ["XML_OUTPUT_FILE"]


def test_other():
    pass
