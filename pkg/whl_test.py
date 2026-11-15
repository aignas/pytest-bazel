"""Check the wheel metadata, which is maintained by hand in pkg/BUILD.bazel."""

import email
import os
import re
import tomllib
import unittest
import zipfile
from pathlib import Path

_DEV_ONLY_EXTRAS = {"docs", "tests"}


def _normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement(req):
    """Normalize a `Requires-Dist` value."""
    req, _, marker = req.partition(";")
    name, sep, extras = req.strip().partition("[")
    return f"{_normalize(name)}{sep}{extras}", marker.strip()


class WheelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Unstamped wheels are named `pytest_bazel-{BUILD_EMBED_LABEL}-...`, which
        # `$(rootpath)` would quote, so find it instead.
        (wheel,) = Path(os.environ["WHEEL_DIR"]).glob("*.whl")
        cls.wheel = zipfile.ZipFile(wheel)
        cls.addClassCleanup(cls.wheel.close)
        cls.dist_info = next(
            n.partition("/")[0] for n in cls.wheel.namelist() if ".dist-info/" in n
        )
        cls.metadata = email.message_from_bytes(
            cls.wheel.read(f"{cls.dist_info}/METADATA")
        )
        with Path(os.environ["PYPROJECT"]).open("rb") as f:
            cls.project = tomllib.load(f)["project"]

    def test_name(self):
        self.assertEqual(
            _normalize(self.metadata["Name"]), _normalize(self.project["name"])
        )

    def test_requires_python(self):
        self.assertEqual(
            self.metadata["Requires-Python"], self.project["requires-python"]
        )

    def test_dependencies_match_pyproject(self):
        got = {_requirement(r) for r in self.metadata.get_all("Requires-Dist")}

        want = {_requirement(r) for r in self.project["dependencies"]}
        for extra, reqs in self.project["optional-dependencies"].items():
            if extra in _DEV_ONLY_EXTRAS:
                continue
            want |= {(_requirement(r)[0], f"extra == '{extra}'") for r in reqs}

        self.assertEqual(got, want)

    def test_extras_match_pyproject(self):
        want = set(self.project["optional-dependencies"]) - _DEV_ONLY_EXTRAS
        self.assertEqual(set(self.metadata.get_all("Provides-Extra")), want)

    def test_self_referencing_extras_use_our_name(self):
        name = _normalize(self.project["name"])
        for req in self.metadata.get_all("Requires-Dist"):
            req_name, _ = _requirement(req)
            if "[" in req_name:
                self.assertEqual(req_name.partition("[")[0], name, req)

    def test_console_script(self):
        entry_points = self.wheel.read(f"{self.dist_info}/entry_points.txt").decode()
        self.assertIn("pytest_bazel = pytest_bazel:main", entry_points)

    def test_sources_are_included(self):
        names = set(self.wheel.namelist())
        for src in ("__init__.py", "__main__.py", "main.py"):
            self.assertIn(f"pytest_bazel/{src}", names)


if __name__ == "__main__":
    unittest.main()
