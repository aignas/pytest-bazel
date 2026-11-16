"""Report paths of plugins are written to TEST_UNDECLARED_OUTPUTS_DIR."""

from pathlib import Path

import pytest

from pytest_bazel.main import BazelEnv, _pytest_args

_OUTPUTS = Path("/outputs").absolute()


def _args(*args):
    env = BazelEnv({"BAZEL_TEST": "1", "TEST_UNDECLARED_OUTPUTS_DIR": str(_OUTPUTS)})
    return _pytest_args(args=list(args), env=env)


@pytest.mark.parametrize("flag", ["--html", "--json-report-file", "--report-log"])
def test_relative_path_goes_to_outputs(flag):
    assert f"{flag}={_OUTPUTS / 'sub' / 'report'}" in _args(f"{flag}=sub/report")


@pytest.mark.parametrize("flag", ["--html", "--json-report-file", "--report-log"])
def test_relative_path_as_separate_arg_goes_to_outputs(flag):
    assert _args(flag, "sub/report")[-2:] == [flag, str(_OUTPUTS / "sub" / "report")]


def test_absolute_path_as_separate_arg_is_kept():
    report = str(Path("/abs/report.html").absolute())

    assert _args("--html", report)[-2:] == ["--html", report]


def test_absolute_path_is_kept():
    report = str(Path("/abs/report.html").absolute())

    assert f"--html={report}" in _args(f"--html={report}")


@pytest.mark.parametrize(
    "arg",
    [
        "--html=",
        "--htmlx=report.html",
        "--junitxml=report.xml",
        "report.html",
    ],
)
def test_other_args_are_kept(arg):
    assert _args(arg)[-1] == arg


def test_kept_without_outputs_dir():
    args = _pytest_args(args=["--html=report.html"], env=BazelEnv({"BAZEL_TEST": "1"}))

    assert args[-1] == "--html=report.html"


def test_does_not_change_the_given_args():
    given = ["--html=report.html"]

    _pytest_args(
        args=given,
        env=BazelEnv({"BAZEL_TEST": "1", "TEST_UNDECLARED_OUTPUTS_DIR": "/out"}),
    )

    assert given == ["--html=report.html"]


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
