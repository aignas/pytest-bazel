## Contributing

This project is very early in terms of maturity level and contributions and feedback are welcome.

## Updating dependencies

Helper scripts for bumping pinned versions live in the `dev` directory. They
require `curl` and `jq` to be available on `PATH`.

- Update `.bazelversion` to the latest stable Bazel release:

  ```shell
  ./dev/update_bazel_version.sh
  ```

- Update the `bazel_dep` versions in `MODULE.bazel` to the latest published
  versions in the [Bazel Central Registry](https://registry.bazel.build/):

  ```shell
  ./dev/update_bazel_deps.sh
  ```

  Afterwards, refresh the lockfile:

  ```shell
  bazel mod deps --lockfile_mode=refresh
  ```
