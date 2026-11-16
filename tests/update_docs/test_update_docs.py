import importlib
import importlib.util
import re
from pathlib import Path

import pytest

# `dev/update_docs` is not a package, its BUILD.bazel puts it on sys.path.
lib = importlib.import_module("lib")
assert lib.__file__ is not None
_spec = importlib.util.spec_from_file_location(
    "update_docs_main", Path(lib.__file__).parent / "__main__.py"
)
assert _spec is not None
assert _spec.loader is not None
update_docs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(update_docs)


_PAGE = """---
pytest_bazel_examples:
  a:
    target: '//examples/a:a_test'
    flags: ['--test_arg=-v']
    keep: 'passed'
---

# A

<!-- run: a -->
<!-- end -->
"""


def _page(tmp_path, text=_PAGE, name="page.md"):
    page = tmp_path / name
    page.write_text(text)
    return page


def test_examples_of_a_page():
    examples = lib.examples_of(_PAGE, Path("page.md"))

    assert examples == {
        "a": lib.Example(
            target="//examples/a:a_test", flags=["--test_arg=-v"], keep="passed"
        )
    }


def test_page_without_frontmatter():
    assert lib.examples_of("# A\n\ntext\n", Path("page.md")) == {}


@pytest.mark.parametrize(
    ("example", "error"),
    [
        pytest.param("    flags: []", "needs a `target`", id="no_target"),
        pytest.param(
            "    target: '//a'\n    kep: 'x'", "unknown keys ['kep']", id="unknown_key"
        ),
        pytest.param(
            "    target: '//a'\n    flags: '--x'",
            "`flags` must be a list of strings",
            id="flags_not_a_list",
        ),
        pytest.param(
            "    target: '//a'\n    keep: '(unclosed'",
            "`keep` is not a valid regex",
            id="bad_regex",
        ),
    ],
)
def test_invalid_examples(example, error):
    text = f"---\npytest_bazel_examples:\n  a:\n{example}\n---\n"

    with pytest.raises(lib.DocsError, match=re.escape(error)):
        lib.examples_of(text, Path("page.md"))


def test_duplicate_examples():
    """YAML would silently use the last one."""
    text = (
        "---\npytest_bazel_examples:\n"
        "  a:\n    target: '//a'\n"
        "  a:\n    target: '//b'\n"
        "---\n"
    )

    with pytest.raises(lib.DocsError, match=r"page.md: duplicate keys \['a'\]"):
        lib.examples_of(text, Path("page.md"))


def test_load_fails_on_run_blocks_without_example(tmp_path):
    page = _page(tmp_path, _PAGE + "<!-- run: b -->\n<!-- end -->\n")

    with pytest.raises(lib.DocsError, match=r"run` blocks \['b'\] have no example"):
        update_docs.load([page])


def test_load_fails_on_examples_without_run_block(tmp_path):
    page = _page(tmp_path, _PAGE.replace("<!-- run: a -->\n<!-- end -->\n", ""))

    with pytest.raises(lib.DocsError, match=r"examples \['a'\] have no `run` block"):
        update_docs.load([page])


def test_names_are_per_page(tmp_path):
    """Two pages can use the same name, as each defines its own examples."""
    pages = [_page(tmp_path, name="one.md"), _page(tmp_path, name="two.md")]

    assert set(update_docs.load(pages)) == set(pages)


def test_examples_of_the_repository():
    """Every page in docs/features defines the examples it runs."""
    pages = sorted(Path("docs/features").glob("*.md"))
    assert pages

    needed = update_docs.load(pages)

    assert sum(len(examples) for examples in needed.values()) > 0


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("===== 1 passed in 0.12s =====", "===== 1 passed in <time> ====="),
        (
            "//examples/a:a_test      PASSED in 1.3s",
            "//examples/a:a_test PASSED in <time>",
        ),
        (
            "/home/u/.cache/bazel/x/execroot/_main/bazel-out/k8-fastbuild/testlogs/a/test.log",
            "bazel-testlogs/a/test.log",
        ),
        ("/x/y/a_test.runfiles/_main/a.py:3", "<runfiles>/_main/a.py:3"),
        (
            '<testsuite timestamp="2026" hostname="h">',
            '<testsuite timestamp="<timestamp>" hostname="<hostname>">',
        ),
        ("trailing   ", "trailing"),
        ("platform linux -- Python 3.9\nkept", "kept"),
        ("rootdir: /x\nplugins: a\ncachedir: c\nkept", "kept"),
    ],
)
def test_sanitize(text, want):
    assert lib.sanitize(text) == want


def test_render_and_update(tmp_path):
    page = tmp_path / "page.md"
    page.write_text("text\n<!-- run: a -->\nold\n<!-- end -->\nmore\n")
    outputs = {page: {"a": "$ bazel test //a\nnew"}}
    want = "text\n<!-- run: a -->\n```console\n$ bazel test //a\nnew\n```\n<!-- end -->\nmore\n"

    assert lib.used_examples(page.read_text()) == ["a"]
    assert lib.render(page.read_text(), outputs[page]) == want
    assert lib.update([page], outputs, check=True) == [page]
    assert "old" in page.read_text()
    assert lib.update([page], outputs, check=False) == [page]
    assert page.read_text() == want
    assert lib.update([page], outputs, check=True) == []


@pytest.mark.parametrize(
    ("line", "want"),
    [
        ("ERROR: /ws/examples/a/BUILD.bazel:3:8: error while validating output", True),
        ("ERROR: /ws/a/BUILD:1:2: Testing //a:b failed", True),
        ("ERROR: --pdb needs a terminal.", False),
        ("ERROR: Build did NOT complete successfully", False),
    ],
)
def test_bazel_errors_are_told_apart_from_test_output(line, want):
    assert bool(lib._BAZEL_ERROR.match(line)) is want


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
