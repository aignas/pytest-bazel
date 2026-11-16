"""Export the bazel pytest wrapper.

Using it as an alternative to `unittest.main()` in a `py_test` rule.

```python
import pytest_bazel

...

if __name__ == "__main__":
    pytest_bazel.main()
```

```starlark
# BUILD.bazel contents
load("@rules_python//python:py_test.bzl", "py_test")

py_test(
    name = "my_test",
    # ...
    deps = ["@pypi//pytest_bazel"],
)
```
"""

import sys

from ._impl.main import main as _main

# The public API, everything else, e.g. in `pytest_bazel._impl`, is private.
__all__ = ["main"]


def main(args=None):
    """Run pytest.

    Args:
    ----
        args: extra args for pytest, added after the ones of pytest_bazel.
            Defaults to `sys.argv[1:]`.

    """
    sys.exit(_main(args=args))
