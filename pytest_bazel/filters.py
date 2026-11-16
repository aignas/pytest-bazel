"""Turn the `--test_filter` of bazel into a pytest `-k` expression."""

from pathlib import PurePosixPath


def _split(text: str, sep: str) -> list[str]:
    """Split `text` at `sep`, but not inside the parameters of a test, `t[...]`."""
    parts = []
    depth = 0
    current = ""
    for char in text:
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        if char == sep and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    return [part for part in parts if part]


def _split_filters(test_filter: str) -> list[str]:
    """Split `a,b` into `a` and `b`, but not the commas of parameters `t[1,2]`."""
    return _split(test_filter, ",")


def _single_keyword_expression(test_filter: str) -> str:
    path, sep, rest = test_filter.partition("::")
    if sep or "/" in path or path.endswith(".py"):
        # A file or a pytest node id, the module name is the file name.
        names = [PurePosixPath(path).name, *rest.split("::")]
    else:
        names = _split(test_filter, ".")

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


def _with_keyword_expression(args: list[str], expression: str) -> list[str]:
    """Return `args` with `-k expression`, combined with a `-k` of the user.

    pytest uses the last `-k` only, so the filter would replace the `-k` in
    the `args` of the target. `-k x`, `-kx` and `-k=x` are recognised, but
    not `-k` combined with other short flags, e.g. `-vk x`.
    """

    def combine(user: str) -> str:
        return f"({user}) and ({expression})" if user.strip() else expression

    for i in reversed(range(len(args))):
        arg = args[i]
        if arg == "-k" and i + 1 < len(args):
            return [*args[: i + 1], combine(args[i + 1]), *args[i + 2 :]]
        if arg.startswith("-k") and len(arg) > len("-k"):
            user = arg[len("-k") :].removeprefix("=")
            return [*args[:i], f"-k{combine(user)}", *args[i + 1 :]]
    return [*args, "-k", expression]
