"""`bazel run //dev/benchmark -- --update` writes its results to README.md."""

import importlib
from pathlib import Path

import pytest

# dev/benchmark is on sys.path, see its BUILD.bazel.
lib = importlib.import_module("lib")
BEGIN, END, ReadmeError = lib.BEGIN, lib.END, lib.ReadmeError
node_ids, replace_block, table = lib.node_ids, lib.replace_block, lib.table

_COUNT = 1000


def test_readme_has_one_block_for_the_results():
    readme = Path("README.md").read_text()

    assert readme.count(BEGIN) == 1
    assert readme.count(END) == 1
    assert readme.index(BEGIN) < readme.index(END)


def test_replace_block():
    text = f"before\n{BEGIN}\nold\nresults\n{END}\nafter\n"

    got = replace_block(text, "new\n")

    assert got == f"before\n{BEGIN}\nnew\n{END}\nafter\n"
    assert replace_block(got, "new") == got


@pytest.mark.parametrize(
    "text",
    ["no block", f"{BEGIN}\n{END}\n{BEGIN}\n{END}\n", f"{BEGIN}\nno end"],
    ids=["missing", "twice", "unclosed"],
)
def test_replace_block_needs_exactly_one_block(text):
    with pytest.raises(ReadmeError):
        replace_block(text, "results")


def test_table():
    assert table([("a", "1 ms")]) == "| What | Time |\n| --- | --- |\n| a | 1 ms |"


def test_node_ids():
    ids = node_ids(_COUNT)

    assert len(ids) == _COUNT
    assert all(".py::" in i and "::test_function_" in i for i in ids)


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
