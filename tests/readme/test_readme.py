"""The README is also the PyPI project description, keep its links working."""

import re
from pathlib import Path

import pytest

_README = Path("README.md")
_FEATURES = Path("docs/features")
_DOCS = "https://pytest-bazel.readthedocs.io/latest/"

_INLINE_LINK = re.compile(r"\]\((?P<url>[^)]+)\)")
_REFERENCE_LINK = re.compile(r"^\[[^]]+\]: (?P<url>\S+)", re.M)
_FEATURE_LINK = re.compile(re.escape(_DOCS) + r"features/(?P<page>[a-z-]+)\.html")


@pytest.fixture(scope="module")
def readme():
    return _README.read_text()


def _urls(text):
    for pattern in (_INLINE_LINK, _REFERENCE_LINK):
        for m in pattern.finditer(text):
            yield m["url"]


def test_links_are_absolute(readme):
    """Relative links do not work on PyPI."""
    relative = [url for url in _urls(readme) if not url.startswith(("https://", "#"))]

    assert relative == []


def test_documentation_links_to_rtd(readme):
    assert re.search(r"^\[documentation\]: " + re.escape(_DOCS) + "$", readme, re.M)


def test_feature_links_point_to_existing_pages(readme):
    pages = {m["page"] for m in _FEATURE_LINK.finditer(readme)}

    missing = sorted(p for p in pages if not (_FEATURES / f"{p}.md").exists())
    assert missing == []


def test_every_feature_page_is_linked(readme):
    pages = {m["page"] for m in _FEATURE_LINK.finditer(readme)}
    documented = {p.stem for p in _FEATURES.glob("*.md")} - {"index"}

    assert sorted(documented - pages) == []


def _cells(row):
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _table_rows(readme, header):
    lines = readme.splitlines()
    start = lines.index(header)
    rows = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        rows.append(line)
    return rows


@pytest.mark.parametrize(
    "header",
    [
        "| Bazel | `pytest_bazel` | Docs | Reference |",
        "| Env var | Default | Default in 1.0 | Description | Docs |",
    ],
)
def test_every_row_links_to_the_docs(readme, header):
    column = _cells(header).index("Docs")
    rows = _table_rows(readme, header)

    assert rows
    for row in rows:
        cell = _cells(row)[column]
        assert "[Example][docs-" in cell or "[Not supported][" in cell, row


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
