import os
from pathlib import Path

import pytest


@pytest.mark.skipif("BAZEL_TEST" not in os.environ, reason="needs bazel test")
def test_tmp_path_is_in_undeclared_outputs(tmp_path):
    outputs = Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"]).resolve()
    assert outputs in tmp_path.resolve().parents


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
