#!/usr/bin/env python3
"""Check that the changelog is up to date for a release.

Usage, from the root of the repository:

    pkg/check_changelog.py <version>
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = "https://github.com/aignas/pytest-bazel"


def check(version: str, changelog: str, news: list[str]) -> list[str]:
    """Return what is missing for `version`, or nothing if it is all there.

    Args:
        version: the version being released, e.g. `0.4.0`.
        changelog: the contents of CHANGELOG.md.
        news: the names of the news entries in news/.

    Returns:
        The problems, one per item.

    """
    v = re.escape(version)
    problems = []
    if not re.search(rf"^## \[{v}\]$", changelog, re.M):
        problems.append(f"CHANGELOG.md has no `## [{version}]` section")
    if not re.search(
        rf"^\[{v}\]: {re.escape(ROOT)}/releases/tag/{v}$", changelog, re.M
    ):
        problems.append(
            f"CHANGELOG.md has no `[{version}]: {ROOT}/releases/tag/{version}` link"
        )
    if not re.search(
        rf"^\[unreleased\]: {re.escape(ROOT)}/compare/{v}\.\.\.HEAD$", changelog, re.M
    ):
        problems.append(
            f"the `[unreleased]` link in CHANGELOG.md does not compare from {version}"
        )
    problems.extend(f"news/{name} is not in CHANGELOG.md yet" for name in sorted(news))
    return problems


def main() -> int:
    """Check the changelog for the version given as an argument."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", help="the version being released, e.g. 0.4.0")
    args = parser.parse_args()

    news = [p.name for p in Path("news").glob("*.md")]
    problems = check(args.version, Path("CHANGELOG.md").read_text(), news)
    if not problems:
        print(f"CHANGELOG.md is up to date for {args.version}")
        return 0

    print(f"ERROR: CHANGELOG.md is not up to date for {args.version}:", file=sys.stderr)
    for problem in problems:
        print(f"  {problem}", file=sys.stderr)
    print(
        "Move the news entries into the changelog before tagging the release.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
