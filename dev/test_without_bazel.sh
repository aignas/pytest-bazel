#!/bin/bash
# Run the unit tests with a given Python without Bazel.
#
# rules_python needs Python 3.9+ to run any py_test, so this is how we test
# the oldest Python we support. Each test file runs through `pytest_bazel`
# with the env vars that `bazel test` would set for it.
#
# Usage: dev/test_without_bazel.sh <python version> <test files...>

set -euo pipefail

cd "$(dirname "$0")/.."

readonly PYTHON="$1"
shift

out="$(mktemp -d)"
trap 'rm -rf "$out"' EXIT

failed=()
for test_file in "$@"; do
  name="$(basename "$test_file" .py)"
  package="$(dirname "$test_file")"
  test_out="$out/$package/$name"
  mkdir -p "$test_out/tmp" "$test_out/outputs"

  # https://bazel.build/reference/test-encyclopedia#initial-conditions
  if ! env \
    BAZEL_TEST=1 \
    TEST_TARGET="//$package:$name" \
    TEST_TMPDIR="$test_out/tmp" \
    TEST_UNDECLARED_OUTPUTS_DIR="$test_out/outputs" \
    XML_OUTPUT_FILE="$test_out/test.xml" \
    uv run --quiet --isolated --no-project --python "$PYTHON" --with pytest \
      python -m pytest_bazel "$test_file"; then
    failed+=("$test_file")
  fi
done

if [[ ${#failed[@]} -gt 0 ]]; then
  echo "FAILED with Python $PYTHON:" >&2
  printf '  %s\n' "${failed[@]}" >&2
  exit 1
fi
echo "All ${#} test files passed with Python $PYTHON"
