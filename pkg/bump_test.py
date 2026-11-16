import pytest

from pkg.bump import WIDTH, BumpError, bump, next_version, pre_release, section
from pkg.check_changelog import REPO_URL, check

_CHANGELOG = f"""# Changelog

## [Unreleased]

Nothing yet.

## [0.4.0]

### Added

- A feature.

[unreleased]: {REPO_URL}/compare/0.4.0...HEAD
[0.4.0]: {REPO_URL}/releases/tag/0.4.0
"""


@pytest.mark.parametrize(
    ("categories", "want"),
    [
        (["fixed"], "0.4.1"),
        (["added", "fixed"], "0.5.0"),
        (["changed"], "0.5.0"),
        (["removed"], "0.5.0"),
    ],
)
def test_next_version(categories, want):
    assert next_version("0.4.0", categories) == want


def test_next_major_version():
    assert next_version("0.5.2", ["fixed"], major_release=True) == "1.0.0"


def test_bump_major_release():
    version, changelog = bump(
        _CHANGELOG, {"12.changed.md": "A change.\n"}, major_release=True
    )

    assert version == "1.0.0"
    assert check("1.0.0", changelog, news=[]) == []


@pytest.mark.parametrize(
    ("kind", "tags", "want"),
    [
        ("rc", [], "1.0.0rc1"),
        ("rc", ["0.5.0", "1.0.0rc1", "1.0.0rc2"], "1.0.0rc3"),
        ("rc", ["1.0.0b1", "1.0.0b2", "1.0.0rc1"], "1.0.0rc2"),
        ("b", ["1.0.0rc1", "1.1.0b4"], "1.0.0b1"),
        ("a", ["1.0.0a9", "1.0.0a10"], "1.0.0a11"),
    ],
)
def test_pre_release(kind, tags, want):
    assert pre_release("1.0.0", kind, tags) == want


def test_bump_fixes_only():
    version, changelog = bump(_CHANGELOG, {"12.fixed.md": "A fix.\n"})

    assert version == "0.4.1"
    assert check("0.4.1", changelog, news=[]) == []
    assert "Nothing yet.\n\n## [0.4.1]\n\n### Fixed\n\n- A fix." in changelog
    assert f"[unreleased]: {REPO_URL}/compare/0.4.1...HEAD\n" in changelog
    assert f"[0.4.1]: {REPO_URL}/releases/tag/0.4.1\n[0.4.0]:" in changelog


def test_bump_with_features():
    version, changelog = bump(
        _CHANGELOG,
        {
            "13.fixed.md": "A fix.\n",
            "12.added.md": "A feature.\n",
            "11.added.md": "B.\n",
        },
    )

    assert version == "0.5.0"
    assert check("0.5.0", changelog, news=[]) == []
    added = changelog.index("### Added")
    assert added < changelog.index("### Fixed")
    # Sorted by the PR number.
    assert changelog.index("[#11]") < changelog.index("[#12]")


def test_section_wraps_entries():
    text = "A long entry " * 10
    got = section("1.0.0", {"fixed": [(7, text)]})

    lines = got.splitlines()
    assert lines[:4] == ["## [1.0.0]", "", "### Fixed", ""]
    assert all(len(line) <= WIDTH for line in lines)
    assert lines[4].startswith("- A long entry")
    assert all(line.startswith("  ") for line in lines[5:-1])
    assert got.endswith(f"[#7]({REPO_URL}/pull/7).\n\n")


@pytest.mark.parametrize(
    ("changelog", "news", "error"),
    [
        (_CHANGELOG, {}, "no news entries"),
        (_CHANGELOG, {"TBD.fixed.md": "x"}, "must be named"),
        (_CHANGELOG, {"1.security.md": "x"}, "must be named"),
        ("# Changelog\n", {"1.fixed.md": "x"}, "no released version"),
        (
            _CHANGELOG.replace("Nothing yet.", "Stuff."),
            {"1.fixed.md": "x"},
            "Unreleased",
        ),
        (
            _CHANGELOG.replace("compare/0.4.0", "compare/0.3.0"),
            {"1.fixed.md": "x"},
            "link",
        ),
    ],
)
def test_errors(changelog, news, error):
    with pytest.raises(BumpError, match=error):
        bump(changelog, news)


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
