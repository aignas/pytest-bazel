"""Run the examples and render the generated blocks of the docs."""

import difflib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml

DOCS = Path("docs/features")
TESTLOGS = Path("bazel-testlogs")

# The examples of a page are in its frontmatter, which MyST ignores:
#
#     ---
#     pytest_bazel_examples:
#       <name>:
#         target: '//examples/<feature>:<target>'
#         flags: ['--test_filter=...']
#     ---
FRONTMATTER = re.compile(r"\A---\n(?P<yaml>.*?\n)---\n", re.S)
EXAMPLES_KEY = "pytest_bazel_examples"

BLOCK = re.compile(
    r"(?P<start><!-- (?P<kind>source|run): (?P<arg>\S+) -->\n)(?P<body>.*?)(?P<end><!-- end -->)",
    re.S,
)

# Lines of the pytest header that depend on the machine or the versions.
# The same for the preamble that bazel adds to the test log.
_DROP = re.compile(
    r"^(platform |rootdir: |plugins: |cachedir: |configfile: "
    r"|exec \$\{PAGER|Executing tests from |-{20,}$"
    # The args change with every new feature, the docs show them where needed.
    r"|Running pytest.main with: )"
)

# (pattern, replacement) to make the output the same on every machine and run.
_SANITIZE = [
    # Paths into the sandbox or the execroot.
    (re.compile(r"/\S*?/testlogs/"), "bazel-testlogs/"),
    (re.compile(r"/\S*?\.runfiles/"), "<runfiles>/"),
    (re.compile(r"/\S*?/_tmp/[0-9a-f]+"), "<TEST_TMPDIR>"),
    (re.compile(r"/tmp/pytest-bazel-\w+"), "/tmp/pytest-bazel-<random>"),
    (re.compile(r"(?<=/tmp/)tmp\w{8}\b"), "tmp<random>"),
    # Durations, e.g. `in 0.12s` and `PASSED in 1.3s`.
    (re.compile(r"\b\d+\.\d+s\b"), "<time>"),
    (re.compile(r"timed out at .* UTC"), "timed out at <date> UTC"),
    (re.compile(r"\b0x[0-9a-f]+\b"), "0x<address>"),
    # Attributes of the JUnit XML that change on every run.
    (re.compile(r'\b(timestamp|hostname|time)="[^"]*"'), r'\1="<\1>"'),
    # Bazel aligns the status of the targets, which depends on the name length.
    (re.compile(r"^(//\S+)\s+"), r"\1 "),
]

_LANGUAGES = {".py": "python", ".ini": "ini", ".bazel": "starlark"}


@dataclass
class Example:
    """A `bazel test` run whose output is shown in the docs."""

    target: str
    flags: list[str] = field(default_factory=list)
    # Files in bazel-testlogs/<target>/ to show, `*` matches shards.
    files: list[str] = field(default_factory=lambda: ["test.log"])
    # Only show the lines of the files that match.
    keep: str = ""
    # List the files in these directories of bazel-testlogs/<target>/.
    list_dirs: list[str] = field(default_factory=list)


class DocsError(Exception):
    """A page or its examples are wrong."""


_FIELDS = {f.name for f in fields(Example)}
_LIST_FIELDS = ("flags", "files", "list_dirs")


class _UniqueKeyLoader(yaml.SafeLoader):
    """Fail on duplicate keys, which YAML would silently overwrite."""

    def construct_mapping(self, node, deep=False):
        keys = [self.construct_object(key, deep=deep) for key, _ in node.value]
        duplicates = sorted({str(key) for key in keys if keys.count(key) > 1})
        if duplicates:
            msg = f"duplicate keys {duplicates}"
            raise DocsError(msg)
        return super().construct_mapping(node, deep=deep)


def _example(where: str, spec: object) -> Example:
    """Make an Example from its frontmatter."""
    if not isinstance(spec, dict):
        msg = f"{where} must be a mapping"
        raise DocsError(msg)
    unknown = sorted(set(spec) - _FIELDS)
    if unknown:
        msg = f"{where} has unknown keys {unknown}, the keys are {sorted(_FIELDS)}"
        raise DocsError(msg)
    if not isinstance(spec.get("target"), str):
        msg = f"{where} needs a `target`"
        raise DocsError(msg)
    for key in _LIST_FIELDS:
        value = spec.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            msg = f"{where}: `{key}` must be a list of strings"
            raise DocsError(msg)
    keep = spec.get("keep", "")
    if not isinstance(keep, str):
        msg = f"{where}: `keep` must be a string"
        raise DocsError(msg)
    try:
        re.compile(keep)
    except re.error as e:
        msg = f"{where}: `keep` is not a valid regex: {e}"
        raise DocsError(msg) from e
    return Example(**spec)


def examples_of(text: str, page: Path) -> dict[str, Example]:
    """Return the examples in the frontmatter of a page."""
    m = FRONTMATTER.match(text)
    if not m:
        return {}
    try:
        data = yaml.load(m["yaml"], Loader=_UniqueKeyLoader) or {}
    except DocsError as e:
        msg = f"{page}: {e}"
        raise DocsError(msg) from e
    examples = data.get(EXAMPLES_KEY) or {}
    if not isinstance(examples, dict):
        msg = f"{page}: `{EXAMPLES_KEY}` must be a mapping"
        raise DocsError(msg)
    return {
        name: _example(f"{page}: example {name!r}", spec)
        for name, spec in examples.items()
    }


def sanitize(text: str) -> str:
    """Drop and rewrite the parts of an output that change between runs."""
    lines = []
    for line in text.splitlines():
        if _DROP.match(line):
            continue
        sanitized = line
        for pattern, replacement in _SANITIZE:
            sanitized = pattern.sub(replacement, sanitized)
        lines.append(sanitized.rstrip())
    return "\n".join(lines)


def _read(path: Path) -> str:
    """Read a test output, indent XML files to make them readable."""
    if path.suffix != ".xml":
        return path.read_text()
    tree = ET.parse(path)
    ET.indent(tree)
    return ET.tostring(tree.getroot(), encoding="unicode")


def _testlogs(target: str) -> Path:
    package, _, name = target.removeprefix("//").partition(":")
    return TESTLOGS / package / name


def run(example: Example) -> str:
    """Run the example and return its command and output for the docs."""
    cmd = ["bazel", "test", example.target, *example.flags]
    result = subprocess.run(
        [
            *cmd,
            "--nocache_test_results",
            "--color=no",
            "--curses=no",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    status = [line for line in output.splitlines() if line.startswith("//")]
    if not status:
        sys.exit(f"ERROR: no test result for {example.target}:\n{output}")

    out = ["$ " + " ".join(cmd), sanitize("\n".join(status))]
    testlogs = _testlogs(example.target)
    keep = re.compile(example.keep) if example.keep else None
    for pattern in example.files:
        for path in sorted(testlogs.glob(pattern)):
            text = sanitize(_read(path))
            if keep:
                text = "\n".join(
                    line for line in text.splitlines() if keep.search(line)
                )
            out += [f"$ cat {path}", text]
    for directory in example.list_dirs:
        root = testlogs / directory
        files = sorted(p for p in root.rglob("*") if p.is_file())
        out += [f"$ find {root} -type f", *(str(p) for p in files)]
    return "\n".join(out)


def _source(path: str) -> str:
    language = _LANGUAGES.get(Path(path).suffix, "")
    text = Path(path).read_text().rstrip()
    return f"```{{code-block}} {language}\n:caption: {path}\n\n{text}\n```"


def render(text: str, outputs: dict[str, str]) -> str:
    """Fill the blocks of a page with the sources and the example outputs."""

    def block(m: re.Match) -> str:
        if m["kind"] == "source":
            body = _source(m["arg"])
        else:
            body = f"```console\n{outputs[m['arg']]}\n```"
        return f"{m['start']}{body}\n{m['end']}"

    return BLOCK.sub(block, text)


def used_examples(text: str) -> list[str]:
    """Return the names of the examples in the `run` blocks of a page."""
    names = (m["arg"] for m in BLOCK.finditer(text) if m["kind"] == "run")
    return list(dict.fromkeys(names))


def update(
    pages: list[Path], outputs: dict[Path, dict[str, str]], check: bool
) -> list[Path]:
    """Render the pages and return the ones that were out of date.

    `outputs` has the outputs of the examples of each page. With `check`, print
    the diff of the pages that are out of date instead of writing them.
    """
    stale = []
    for page in pages:
        old = page.read_text()
        new = render(old, outputs.get(page, {}))
        if new == old:
            continue
        stale.append(page)
        if check:
            sys.stdout.writelines(
                difflib.unified_diff(
                    old.splitlines(keepends=True),
                    new.splitlines(keepends=True),
                    str(page),
                    str(page),
                )
            )
        else:
            page.write_text(new)
    return stale
