"""Turn the `--test_filter` of bazel into a pytest `-k` expression."""

from pathlib import PurePosixPath


def _split_filters(test_filter: str) -> list[str]:
    """Split `a,b` into `a` and `b`, but not the commas of parameters `t[1,2]`."""
    parts = []
    depth = 0
    current = ""
    for char in test_filter:
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    return [part for part in parts if part]


def _single_keyword_expression(test_filter: str) -> str:
    path, sep, rest = test_filter.partition("::")
    if sep or "/" in path or path.endswith(".py"):
        # A file or a pytest node id, the module name is the file name.
        names = [PurePosixPath(path).name, *rest.split("::")]
    else:
        names = test_filter.split(".")

    return " and ".join(name for name in names if name)


def _keyword_expression(test_filter: str) -> str:
    """Turn the value of `--test_filter` into a pytest `-k` expression.

    `-k` matches each word against the names of a test and of its parents, so
    split the filter into those names:
    * `TestClass.test_fn`, `TestClass::test_fn` -> `TestClass and test_fn`
    * `test_mod.test_fn` -> `test_mod and test_fn`
    * `dir/test_mod.py::test_fn` -> `test_mod.py and test_fn`
    * `test_a,TestClass.test_b` -> `(test_a) or (TestClass and test_b)`

    A filter with spaces, e.g. `foo or bar`, is already a `-k` expression.
    """
    if not test_filter or " " in test_filter:
        return test_filter

    expressions = [_single_keyword_expression(f) for f in _split_filters(test_filter)]
    if len(expressions) == 1:
        return expressions[0]
    return " or ".join(f"({expression})" for expression in expressions)
