"""Check the wheel metadata, which is maintained by hand in pkg/BUILD.bazel."""

import email
import os
import re
import zipfile
from pathlib import Path

import pytest

# Runs on Python 3.12, see pkg/BUILD.bazel, but pyrefly checks against 3.9.
import tomllib  # pyrefly: ignore[missing-import]

_DEV_ONLY_EXTRAS = {"docs", "tests"}


def _normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement(req):
    """Return a normalized `(requirement, marker)` for a `Requires-Dist` value."""
    req, _, marker = req.partition(";")
    name, sep, extras = req.strip().partition("[")
    return f"{_normalize(name)}{sep}{extras}", marker.strip()


@pytest.fixture(scope="module")
def wheel():
    # Unstamped wheels are named `pytest_bazel-{BUILD_EMBED_LABEL}-...`, which
    # `$(rootpath)` would quote, so find it instead.
    (path,) = Path(os.environ["WHEEL_DIR"]).glob("*.whl")
    with zipfile.ZipFile(path) as whl:
        yield whl


@pytest.fixture(scope="module")
def dist_info(wheel):
    return next(n.partition("/")[0] for n in wheel.namelist() if ".dist-info/" in n)


@pytest.fixture(scope="module")
def metadata(wheel, dist_info):
    return email.message_from_bytes(wheel.read(f"{dist_info}/METADATA"))


@pytest.fixture(scope="module")
def project():
    with Path(os.environ["PYPROJECT"]).open("rb") as f:
        return tomllib.load(f)["project"]


def test_name(metadata, project):
    assert _normalize(metadata["Name"]) == _normalize(project["name"])


def test_requires_python(metadata, project):
    assert metadata["Requires-Python"] == project["requires-python"]


def test_classifiers_match_pyproject(metadata, project):
    assert metadata.get_all("Classifier") == project["classifiers"]


def test_dependencies_match_pyproject(metadata, project):
    got = {_requirement(r) for r in metadata.get_all("Requires-Dist")}

    want = {_requirement(r) for r in project["dependencies"]}
    for extra, reqs in project["optional-dependencies"].items():
        if extra in _DEV_ONLY_EXTRAS:
            continue
        for req in reqs:
            want.add((_requirement(req)[0], f"extra == '{extra}'"))

    assert got == want


def test_extras_match_pyproject(metadata, project):
    want = set(project["optional-dependencies"]) - _DEV_ONLY_EXTRAS
    assert set(metadata.get_all("Provides-Extra")) == want


def test_self_referencing_extras_use_our_name(metadata, project):
    name = _normalize(project["name"])
    for req in metadata.get_all("Requires-Dist"):
        req_name, _ = _requirement(req)
        if "[" in req_name:
            assert req_name.partition("[")[0] == name, req


def test_console_script(wheel, dist_info):
    entry_points = wheel.read(f"{dist_info}/entry_points.txt").decode()
    assert "pytest_bazel = pytest_bazel:main" in entry_points


@pytest.mark.parametrize("src", ["__init__.py", "__main__.py", "main.py"])
def test_sources_are_included(wheel, src):
    assert f"pytest_bazel/{src}" in wheel.namelist()


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
