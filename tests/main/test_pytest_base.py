from pytest_bazel import main


def mock_pytest_main(args=None, collect_args=None, return_exit=0):
    if args and collect_args is not None:
        collect_args.extend(args)

    return return_exit


def test_pytest_default_args():
    got_args = []
    main(
        pytest_main=lambda args: mock_pytest_main(args, collect_args=got_args),
        sys_exit=lambda _: ...,
    )

    got_tmpdir = got_args.pop(-1)
    got_junitxml = got_args.pop(-1)
    assert [
        "--ignore=external",
        "--ignore-glob=**/site-packages",
        "-p",
        "no:cacheprovider",
    ] == got_args
    assert got_junitxml.endswith("test_pytest_base/test.xml")
    assert got_tmpdir.endswith("/pytest")


if __name__ == "__main__":
    main()
