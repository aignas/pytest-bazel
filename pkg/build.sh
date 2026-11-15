#!/bin/bash
# Build the release wheel with the given version and copy it to a dir.
#
# Usage: pkg/build.sh <version> <out_dir>

set -euo pipefail

cd "$(dirname "$0")/.."

readonly VERSION="$1"
readonly OUT_DIR="$2"
readonly WHEEL="bazel-bin/pkg/dist/pytest_bazel-$VERSION-py3-none-any.whl"

bazel build --stamp "--embed_label=$VERSION" //pkg:whl.dist

# Fail early if the version did not make it into the wheel, PyPI would
# otherwise reject the upload or we would publish the wrong version.
if [[ ! -f "$WHEEL" ]]; then
  echo "ERROR: $WHEEL was not built, got:" >&2
  ls bazel-bin/pkg/dist >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
cp "$WHEEL" "$OUT_DIR/"
chmod u+w "$OUT_DIR/$(basename "$WHEEL")"
