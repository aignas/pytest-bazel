#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

readonly BAZELVERSION_FILE=".bazelversion"
readonly RELEASES_API="https://api.github.com/repos/bazelbuild/bazel/releases/latest"

# Fetch the latest stable Bazel release. The `/releases/latest` endpoint already
# excludes prereleases, but validate the tag just in case.
LATEST=$(
    curl -fsSL "${RELEASES_API}" | jq -r '.tag_name'
)
readonly LATEST

if [[ ! "${LATEST}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "error: could not determine a stable Bazel version (got '${LATEST}')" >&2
    exit 1
fi

CURRENT=$(tr -d '[:space:]' < "${BAZELVERSION_FILE}")
readonly CURRENT

if [[ "${CURRENT}" == "${LATEST}" ]]; then
    echo "Bazel is already up to date (${CURRENT})"
    exit 0
fi

echo "${LATEST}" > "${BAZELVERSION_FILE}"
echo "Updated Bazel ${CURRENT} -> ${LATEST}"
