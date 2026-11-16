import sys

import pytest

from pkg.check_changelog import REPO_URL, check, main

_SYNCED = f"""# Changelog

## [Unreleased]

Nothing yet.

## [0.4.0]

### Added

- A feature.

[unreleased]: {REPO_URL}/compare/0.4.0...HEAD
[0.4.0]: {REPO_URL}/releases/tag/0.4.0
"""


def test_synced():
    assert check("0.4.0", _SYNCED, news=[]) == []


@pytest.mark.parametrize(
    ("changelog", "news", "want"),
    [
        pytest.param(
            _SYNCED.replace("## [0.4.0]", "## [0.3.0]"),
            [],
            ["CHANGELOG.md has no `## [0.4.0]` section"],
            id="no_section",
        ),
        pytest.param(
            _SYNCED.replace(f"[0.4.0]: {REPO_URL}/releases/tag/0.4.0\n", ""),
            [],
            [f"CHANGELOG.md has no `[0.4.0]: {REPO_URL}/releases/tag/0.4.0` link"],
            id="no_link",
        ),
        pytest.param(
            _SYNCED.replace("compare/0.4.0...HEAD", "compare/0.3.0...HEAD"),
            [],
            ["the `[unreleased]` link in CHANGELOG.md does not compare from 0.4.0"],
            id="old_unreleased_link",
        ),
        pytest.param(
            _SYNCED,
            ["51.added.md", "50.fixed.md"],
            [
                "news/50.fixed.md is not in CHANGELOG.md yet",
                "news/51.added.md is not in CHANGELOG.md yet",
            ],
            id="news_left",
        ),
    ],
)
def test_not_synced(changelog, news, want):
    assert check("0.4.0", changelog, news) == want


def test_version_is_not_a_regex():
    assert check("0.4.0", _SYNCED.replace("0.4.0", "0x4y0"), news=[]) != []


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / "news").mkdir()
    (tmp_path / "news" / ".gitkeep").touch()
    (tmp_path / "CHANGELOG.md").write_text(_SYNCED)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_main_passes(repo, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["check_changelog.py", "0.4.0"])

    assert main() == 0
    assert "up to date for 0.4.0" in capsys.readouterr().out


def test_main_fails(repo, monkeypatch, capsys):
    (repo / "news" / "52.fixed.md").write_text("A fix.\n")
    monkeypatch.setattr(sys, "argv", ["check_changelog.py", "0.5.0"])

    assert main() == 1
    err = capsys.readouterr().err
    assert "not up to date for 0.5.0" in err
    assert "no `## [0.5.0]` section" in err
    assert "news/52.fixed.md is not in CHANGELOG.md yet" in err


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
