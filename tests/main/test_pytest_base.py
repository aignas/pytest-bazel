from pytest_bazel import main


def mock_pytest_main(args=None, collect_args=None, return_exit=0):
    if args and collect_args is not None:
        collect_args.extend(args)

    return return_exit


def test_pytest_default_args():
    got_args = []
    main(
        pytest_main=lambda args: mock_pytest_main(args, collect_args=got_args),
    )

    assert got_args[:4] == [
        "--ignore=external",
        "--ignore-glob=**/site-packages",
        "-p",
        "no:cacheprovider",
    ], f"unexpected args: {got_args}"

    got_junitxml = [arg for arg in got_args if arg.startswith("--junitxml")][0]
    assert got_junitxml.endswith("test_pytest_base/test.xml")
    got_tmpdir = [arg for arg in got_args if arg.startswith("--basetemp")][0]
    assert got_tmpdir.endswith("/pytest")


def test_pytest_extra_args_passed():
    got_args = []
    main(
        args=["super", "custom", "args"],
        pytest_main=lambda args: mock_pytest_main(args, collect_args=got_args),
    )

    assert ["super", "custom", "args"] == got_args[-3:]


def test_return_non_zero_exit():
    got_exit_code = []
    main(
        pytest_main=lambda args: mock_pytest_main(args, return_exit=42),
        sys_exit=lambda code: got_exit_code.append(code),
    )

    assert got_exit_code == [42]


if __name__ == "__main__":
    main()
