#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Bump the version
readonly VERSION="$1"
readonly ROOT="https://github.com/aignas/pytest-bazel"
readonly CHANGELOG=CHANGELOG.md

# Create a new entry for changelog:
# * The currently unreleased should get the value.
# * The extra text should be inserted at the top.
# * The links at the bottom should be updated
sed \
    -e "s/## \[Unreleased\]/## [Unreleased\n\nNothing yet.\n\n## [$VERSION]/g" \
    -e "s|\[unreleased\]:.*|[unreleased]: $ROOT/compare/$VERSION...HEAD\n[$VERSION]: $ROOT/releases/tag/$VERSION|g" \
    "${CHANGELOG}" > "${CHANGELOG}.new"
mv "${CHANGELOG}.new" "${CHANGELOG}"

# Update the version in the `pkg/BUILD.bazel`
echo "VERSION = \"$VERSION\"" > version.bzl

# Git commit, tag and push
git commit -am "release: $VERSION"
git push
git tag $VERSION
git push --tags
