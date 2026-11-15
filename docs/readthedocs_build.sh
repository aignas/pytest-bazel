#!/bin/bash

set -eou pipefail

# Only forward the env vars that docs/conf.py reads, so that volatile
# per-container vars (e.g. HOSTNAME) do not bust the action cache.
declare -a extra_env=()
for name in \
  READTHEDOCS \
  READTHEDOCS_GIT_COMMIT_HASH \
  READTHEDOCS_GIT_IDENTIFIER \
  READTHEDOCS_VERSION; do
  extra_env+=("--@sphinxdocs//sphinxdocs:extra_env=$name=${!name:-}")
done

set -x
bazel run \
  --config=rtd \
  "--@sphinxdocs//sphinxdocs:extra_defines=version=$READTHEDOCS_VERSION" \
  "${extra_env[@]}" \
  //docs:readthedocs_install
