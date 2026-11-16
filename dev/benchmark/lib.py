"""Helpers of `bazel run //dev/benchmark`, kept apart to test them."""

import re

BEGIN = "<!-- benchmark -->"
END = "<!-- end benchmark -->"

_BLOCK = re.compile(re.escape(BEGIN) + r"\n.*?" + re.escape(END), re.S)


class ReadmeError(Exception):
    """README.md has no block for the results."""


def replace_block(text: str, block: str) -> str:
    """Return `text` with the results between the benchmark markers replaced."""
    if len(_BLOCK.findall(text)) != 1:
        msg = f"README.md needs exactly one block from {BEGIN} to {END}"
        raise ReadmeError(msg)
    return _BLOCK.sub(lambda _: f"{BEGIN}\n{block.strip()}\n{END}", text)


def node_ids(count: int) -> list[str]:
    """Return `count` node ids like the ones of a large repository."""
    ids = []
    for i in range(count):
        path = f"src/team{i % 7}/service{i % 13}/tests/test_module_{i % 50}.py"
        cls = f"TestThing{i % 9}::" if i % 3 else ""
        param = f"[case-{i % 11}-{i % 5}.5]" if i % 4 == 0 else ""
        ids.append(f"{path}::{cls}test_function_{i % 97}{param}")
    return ids


def table(rows: list[tuple[str, str]]) -> str:
    """Return a markdown table of `(what, time)` rows."""
    lines = ["| What | Time |", "| --- | --- |"]
    lines.extend(f"| {what} | {time} |" for what, time in rows)
    return "\n".join(lines)
