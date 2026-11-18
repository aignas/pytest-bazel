"""Turn the `--test_filter` of bazel into a pytest `-k` expression."""

from pathlib import PurePosixPath
from typing import Optional


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


def _split_names(test_filter: str) -> tuple[str, list[str]]:
    """Split e.g. `dir/mod.py::A::t[a/b]` into its path and names, `["A", "t[a/b]"]`.

    The path is empty if there is none, e.g. for `mod.A::t[a/b]`, which is
    split at the dots and the `::`. The parameters of a test come last and may
    contain any character, e.g. `/` or `::`, they stay with the name of the test.
    """
    head, bracket, params = test_filter.partition("[")
    path, sep, rest = head.partition("::")
    if "/" in path or path.endswith(".py"):
        names = rest.split("::") if sep else []
    else:
        path, names = "", head.replace("::", ".").split(".")
    if bracket:
        if names:
            names[-1] += bracket + params
        else:
            path += bracket + params
    return path, names


def _single_keyword_expression(test_filter: str) -> str:
    path, names = _split_names(test_filter)
    if path:
        # A file or a pytest node id, the module name is the file name.
        names = [PurePosixPath(path).name, *names]

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


# Short flags of pytest without a value, which can come before an option with
# a value in e.g. `-vk expression` or `-vc pytest.ini`.
_SHORT_FLAGS = frozenset("vqsxl")


def _split_short_option(arg: str, option: str) -> Optional[tuple[str, Optional[str]]]:
    """Split e.g. `-k`, `-kx`, `-k=x` or `-vkx` into the flags before it and its value.

    `option` is the letter of the short option, e.g. `k`. Return None if `arg`
    has no such option. The value is None if it is the next arg.
    """
    if not arg.startswith("-") or arg.startswith("--"):
        return None
    flags, found, value = arg[1:].partition(option)
    if not found or not set(flags) <= _SHORT_FLAGS:
        return None
    # Like argparse, which drops the `=` of `-k=x`.
    return f"-{flags}", (value.removeprefix("=") if value else None)


def _with_keyword_expression(args: list[str], expression: str) -> list[str]:
    """Return `args` with `-k expression`, combined with a `-k` of the user.

    pytest uses the last `-k` only, so the filter would replace the `-k` in
    the `args` of the target. `-k x`, `-kx`, `-k=x` and `-vk x` are
    recognised.
    """

    def combine(user: str) -> str:
        return f"({user}) and ({expression})" if user.strip() else expression

    for i in reversed(range(len(args))):
        split = _split_short_option(args[i], "k")
        if split is None:
            continue
        flags, value = split
        before = [] if flags == "-" else [flags]
        if value is not None:
            return [*args[:i], *before, f"-k{combine(value)}", *args[i + 1 :]]
        if i + 1 < len(args):
            return [*args[:i], *before, "-k", combine(args[i + 1]), *args[i + 2 :]]
    return [*args, "-k", expression]
