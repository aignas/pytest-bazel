#!/usr/bin/env python3
"""Prepare CHANGELOG.md for the next release from the entries in news/.

The version is the next patch version if all entries are `fixed`, and the
next minor version otherwise. The entries are moved into a new section of
CHANGELOG.md and the release links are updated, so that
`pkg/check_changelog.py <version>` passes.

Usage:

    bazel run //pkg:bump            # update CHANGELOG.md, delete the news
    bazel run //pkg:bump -- --dry-run  # only print the version and section

or `python3 -m pkg.bump` from the root of the repository.
"""

import argparse
import os
import re
import sys
import textwrap
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Optional

from pkg.check_changelog import REPO_URL, check

# The width of the changelog entries.
WIDTH = 80

# The categories of the news entries, in the order of Keep a Changelog.
CATEGORIES = ("added", "changed", "removed", "fixed")

_NEWS = re.compile(r"^(?P<pr>\d+)\.(?P<category>[a-z]+)\.md$")
_VERSION = re.compile(r"^## \[(?P<version>\d+\.\d+\.\d+)\]$", re.M)
_UNRELEASED = "## [Unreleased]\n\nNothing yet.\n\n"


class BumpError(Exception):
    """The changelog or the news entries cannot be released."""


def news_entries(
    names_and_texts: Mapping[str, str],
) -> dict[str, list[tuple[int, str]]]:
    """Return the `(pr, text)` entries per category, sorted by PR number."""
    entries: dict[str, list[tuple[int, str]]] = {}
    for name, text in names_and_texts.items():
        match = _NEWS.match(name)
        if not match or match["category"] not in CATEGORIES:
            msg = f"news/{name} must be named <PR number>.<{'|'.join(CATEGORIES)}>.md"
            raise BumpError(msg)
        entries.setdefault(match["category"], []).append(
            (int(match["pr"]), " ".join(text.split()))
        )
    if not entries:
        msg = "there are no news entries to release"
        raise BumpError(msg)
    return {c: sorted(entries[c]) for c in CATEGORIES if c in entries}


def last_version(changelog: str) -> str:
    """Return the last released version in `changelog`."""
    match = _VERSION.search(changelog)
    if not match:
        msg = "CHANGELOG.md has no released version"
        raise BumpError(msg)
    return match["version"]


def next_version(version: str, categories: Collection[str]) -> str:
    """Return the next patch version if all `categories` are fixes, else minor."""
    major, minor, patch = (int(part) for part in version.split("."))
    if set(categories) == {"fixed"}:
        return f"{major}.{minor}.{patch + 1}"
    return f"{major}.{minor + 1}.0"


def section(version: str, entries: Mapping[str, list[tuple[int, str]]]) -> str:
    """Return the CHANGELOG.md section of `version` for the news `entries`."""
    lines = [f"## [{version}]", ""]
    for category, items in entries.items():
        lines.extend([f"### {category.capitalize()}", ""])
        for pr, text in items:
            entry = f"{text} [#{pr}]({REPO_URL}/pull/{pr})."
            lines.extend(
                textwrap.wrap(
                    entry,
                    width=WIDTH,
                    initial_indent="- ",
                    subsequent_indent="  ",
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def bump(changelog: str, news: dict[str, str]) -> tuple[str, str]:
    """Return the next version and `changelog` with the `news` released in it."""
    previous = last_version(changelog)
    entries = news_entries(news)
    version = next_version(previous, list(entries))

    if _UNRELEASED not in changelog:
        msg = f"CHANGELOG.md has no `{_UNRELEASED.strip()}` section to release from"
        raise BumpError(msg)
    unreleased_link = f"[unreleased]: {REPO_URL}/compare/{previous}...HEAD\n"
    if unreleased_link not in changelog:
        msg = f"CHANGELOG.md has no `{unreleased_link.strip()}` link"
        raise BumpError(msg)

    changelog = changelog.replace(
        _UNRELEASED, _UNRELEASED + section(version, entries), 1
    ).replace(
        unreleased_link,
        f"[unreleased]: {REPO_URL}/compare/{version}...HEAD\n"
        f"[{version}]: {REPO_URL}/releases/tag/{version}\n",
        1,
    )

    problems = check(version, changelog, news=[])
    if problems:
        raise BumpError("\n".join(problems))
    return version, changelog


def main(argv: Optional[list[str]] = None) -> int:
    """Update CHANGELOG.md and delete the released news entries."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run", action="store_true", help="only print what would change"
    )
    args = parser.parse_args(argv)

    # `bazel run` starts the script in its runfiles.
    workspace = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace:
        os.chdir(workspace)

    changelog_path = Path("CHANGELOG.md")
    news_paths = sorted(Path("news").glob("*.md"))
    news = {p.name: p.read_text() for p in news_paths}
    try:
        version, changelog = bump(changelog_path.read_text(), news)
    except BumpError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(version)
        print(section(version, news_entries(news)), end="")
        return 0

    changelog_path.write_text(changelog)
    for path in news_paths:
        path.unlink()
    print(version)
    print(
        f"Updated CHANGELOG.md for {version}. Commit it as "
        f"`docs: prepare the changelog for the {version} release`, and tag "
        f"{version} once it is merged.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
