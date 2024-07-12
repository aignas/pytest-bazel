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

from .main import main

__all__ = [
    "main",
]
