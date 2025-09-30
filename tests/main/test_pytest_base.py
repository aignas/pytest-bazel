import pytest
import warnings
from pathlib import Path

from pytest_bazel.main import _supports_sharding
from pytest_bazel.main import BazelEnv
from pytest_bazel.main import main as _main

@pytest.fixture
def mock_supports_sharding():
    """Mock _supports_sharding to always return True."""

    def mock_supports_sharding_fn():
        return True

    previous_supports_sharding = _supports_sharding.__code__
    _supports_sharding.__code__ = mock_supports_sharding_fn.__code__

    yield

    _supports_sharding.__code__ = previous_supports_sharding

def mock_pytest_main(args=None, collect_args=None, return_exit=0):
    if args and collect_args is not None:
        collect_args.extend(args)

    return return_exit


def test_pytest_default_args():
    got_args = []
    _main(
        pytest_main=lambda args: mock_pytest_main(args, collect_args=got_args),
    )

    assert got_args[:4] == [
        "--ignore=external",
        "--ignore-glob=**/site-packages",
        "-p",
        "no:cacheprovider",
    ], f"unexpected args: {got_args}"

    got_junitxml = next(arg for arg in got_args if arg.startswith("--junitxml"))
    assert got_junitxml.endswith("test_pytest_base/test.xml")
    got_tmpdir = next(arg for arg in got_args if arg.startswith("--basetemp"))
    assert got_tmpdir.endswith("/pytest")


def test_pytest_extra_args_passed():
    got_args = []
    _main(
        args=["super", "custom", "args"],
        pytest_main=lambda args: mock_pytest_main(args, collect_args=got_args),
    )

    assert got_args[-3:] == ["super", "custom", "args"]


def test_return_non_zero_exit():
    want = 42
    assert (
        _main(
            pytest_main=lambda args: mock_pytest_main(args, return_exit=42),
        )
        == want
    )


def test_no_sharding_by_default(tmpdir):
    shard_status_file = Path(tmpdir) / "mock_file"
    _main(
        pytest_main=lambda args: mock_pytest_main(args),
        env=BazelEnv(
            {
                "TEST_SHARD_INDEX": "1",
                "TEST_TOTAL_SHARDS": "2",
                "TEST_SHARD_STATUS_FILE": str(shard_status_file),
                "BAZEL_TEST": "1",
            }
        ),
    )

    assert (
        not shard_status_file.exists()
    ), "Sharding should not be advertised as supported"

@pytest.mark.parametrize(
    ("shard_index", "total_shards"),
    [
        (0, 2),
        (1, 2),
        (2, 2),
    ],
)
def test_sharding_enabled(tmpdir, mock_supports_sharding, shard_index: int, total_shards: int):
    """Ensure that sharding and working when supported."""

    shard_status_file = Path(tmpdir) / f"mock_file_{shard_index}"
    _main(
        pytest_main=lambda args: mock_pytest_main(args),
        env=BazelEnv(
            {
                "TEST_SHARD_INDEX": str(shard_index),
                "TEST_TOTAL_SHARDS": str(total_shards),
                "TEST_SHARD_STATUS_FILE": str(shard_status_file),
                "BAZEL_TEST": "1",
            }
        ),
    )

    assert shard_status_file.exists(), "Sharding should be advertised as supported"

def test_pytest_showwarning():
    """Ensure that the original warning function is restored after pytest runs."""

    original_showwarning = warnings.showwarning

    got_args = []
    _main(
        pytest_main=lambda args: mock_pytest_main(args, collect_args=got_args),
    )
    assert warnings.showwarning == original_showwarning

    _main(
        pytest_main=lambda args: mock_pytest_main(args, return_exit=42),
    )
    assert warnings.showwarning == original_showwarning


if __name__ == "__main__":
    from pytest_bazel import main

    main()
