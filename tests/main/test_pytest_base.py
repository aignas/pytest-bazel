from pathlib import Path

from pytest_bazel.main import BazelEnv
from pytest_bazel.main import main as _main


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


if __name__ == "__main__":
    from pytest_bazel import main

    main()
