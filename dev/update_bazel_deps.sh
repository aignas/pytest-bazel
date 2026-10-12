#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

readonly MODULE_FILE="MODULE.bazel"
readonly BCR="https://bcr.bazel.build/modules"

# Print the latest non-prerelease, non-yanked version of a BCR module.
# Exits with a non-zero status if the module is unknown to the registry.
latest_version() {
    local name="$1" metadata

    if ! metadata=$(curl -fsSL "${BCR}/${name}/metadata.json" 2>/dev/null); then
        return 1
    fi

    jq -r '
        (.yanked_versions // {} | keys) as $yanked
        | [ .versions[]
            | select(test("^[0-9]+(\\.[0-9]+)*$"))
            | select(. as $v | $yanked | index($v) | not)
          ]
        | last // empty
    ' <<<"${metadata}"
}

tmp=$(mktemp)
trap 'rm -f "${tmp}"' EXIT

changed=0
while IFS= read -r line; do
    if [[ "${line}" == *"bazel_dep("* ]]; then
        name=$(sed -n 's/.*name = "\([^"]*\)".*/\1/p' <<<"${line}")
        current=$(sed -n 's/.*version = "\([^"]*\)".*/\1/p' <<<"${line}")

        if [[ -n "${name}" && -n "${current}" ]]; then
            if ! latest=$(latest_version "${name}"); then
                echo "warning: ${name} is not in the Bazel Central Registry, skipping" >&2
                latest=""
            fi

            if [[ -n "${latest}" && "${latest}" != "${current}" ]]; then
                echo "  ${name}: ${current} -> ${latest}" >&2
                line=${line/version = \"${current}\"/version = \"${latest}\"}
                changed=1
            fi
        fi
    fi
    printf '%s\n' "${line}" >> "${tmp}"
done < "${MODULE_FILE}"

if (( changed )); then
    mv "${tmp}" "${MODULE_FILE}"
    echo "Updated ${MODULE_FILE}"
    echo "Run 'bazel mod deps --lockfile_mode=refresh' to refresh MODULE.bazel.lock"
else
    echo "All bazel_dep versions are up to date"
fi
