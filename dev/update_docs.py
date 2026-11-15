#!/usr/bin/env python3
"""Update the generated parts of docs/features/*.md by running the examples.

The docs contain blocks between markers that this script fills in:

    <!-- source: examples/test_filter/test_filter.py -->
    ...the contents of the file...
    <!-- end -->

    <!-- run: test_filter -->
    ...the bazel command of the example in EXAMPLES and its output...
    <!-- end -->

Usage, from the root of the repository:

    dev/update_docs.py          # update the docs
    dev/update_docs.py --check  # fail if the docs are out of date
"""

import argparse
import difflib
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

DOCS = Path("docs/features")
TESTLOGS = Path("bazel-testlogs")

_BLOCK = re.compile(
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


EXAMPLES = {
    "test_filter": Example(
        "//examples/test_filter:test_filter_test", ["--test_filter=TestMath.test_add"]
    ),
    "fail_fast": Example(
        "//examples/fail_fast:fail_fast_test", ["--test_runner_fail_fast"]
    ),
    "sharding": Example(
        "//examples/sharding:sharding_test",
        files=["shard_*_of_3/test.log"],
        keep=r"^collected|passed",
    ),
    "more_shards_than_tests": Example(
        "//examples/sharding:more_shards_than_tests_test",
        files=["shard_*_of_8/test.log"],
        keep=r"passed|deselected",
    ),
    "runs_per_test": Example(
        "//examples/runs_per_test:runs_per_test_test",
        ["--runs_per_test=3", "--test_arg=-s"],
        files=["run_*_of_3/test.log"],
        keep=r"randomly-seed|random number",
    ),
    "junit_xml": Example("//examples/junit_xml:junit_xml_test", files=["test.xml"]),
    "timeout": Example(
        "//examples/timeout:timeout_test",
        ["--test_timeout=3"],
        # Not the frames of rules_python and pytest_bazel, which change often.
        keep=r"SIGTERM|Thread|test_timeout.py|!+ KeyboardInterrupt|passed",
    ),
    "tmpdir": Example("//examples/tmpdir:tmpdir_test", ["--test_arg=-s"], keep=r":\s"),
    "premature_exit": Example("//examples/premature_exit:premature_exit_test"),
    "infrastructure_failure": Example(
        "//examples/infrastructure_failure:infrastructure_failure_test",
        files=["test.log", "test.infrastructure_failure"],
        keep=r"error:|infrastructure|could not run",
    ),
    "annotations": Example(
        "//examples/annotations:annotations_test",
        files=["test.outputs_manifest/ANNOTATIONS"],
    ),
    "warnings": Example(
        "//examples/warnings:warnings_test",
        keep=r"warnings summary|::test_|Warning|warnings.warn",
    ),
    # The workers report in a random order, so only show the summary.
    "xdist": Example("//examples/xdist:xdist_test", keep=r"workers \[|passed"),
    "xdist_timeout": Example(
        "//examples/xdist:xdist_hangs_test",
        ["--test_timeout=3"],
        keep=r"SIGTERM|Stacks of the pytest-xdist|test_xdist_hangs.py.* in ",
    ),
    "keep_failed_tmp_path": Example(
        "//examples/keep_failed_tmp_path:keep_failed_tmp_path_test",
        keep=r"^FAILED|failed",
        list_dirs=["test.outputs"],
    ),
    "scope_collection_default": Example(
        "//examples/scope_collection:default_test",
        ["--test_arg=-v"],
        keep=r"PASSED|FAILED",
    ),
    "scope_collection": Example(
        "//examples/scope_collection:scoped_test",
        ["--test_arg=-v"],
        keep=r"PASSED|FAILED",
    ),
    "config_from_package_default": Example(
        "//examples/config_from_package:default_test", keep=r"passed|PASSED"
    ),
    "config_from_package": Example(
        "//examples/config_from_package:config_from_package_test", keep=r"passed|PASSED"
    ),
    "namespace_packages_default": Example(
        "//examples/namespace_packages:default_test", keep=r"module name"
    ),
    "namespace_packages": Example(
        "//examples/namespace_packages:namespace_packages_test", keep=r"module name"
    ),
}


def _sanitize(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if _DROP.match(line):
            continue
        sanitized = line
        for pattern, replacement in _SANITIZE:
            sanitized = pattern.sub(replacement, sanitized)
        lines.append(sanitized.rstrip())
    return "\n".join(lines)


def _testlogs(target: str) -> Path:
    package, _, name = target.removeprefix("//").partition(":")
    return TESTLOGS / package / name


def _run(example: Example) -> str:
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

    out = ["$ " + " ".join(cmd), _sanitize("\n".join(status))]
    testlogs = _testlogs(example.target)
    keep = re.compile(example.keep) if example.keep else None
    for pattern in example.files:
        for path in sorted(testlogs.glob(pattern)):
            text = _sanitize(path.read_text())
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


def _render(text: str, outputs: dict[str, str]) -> str:
    def block(m: re.Match) -> str:
        if m["kind"] == "source":
            body = _source(m["arg"])
        else:
            body = f"```console\n{outputs[m['arg']]}\n```"
        return f"{m['start']}{body}\n{m['end']}"

    return _BLOCK.sub(block, text)


def main() -> int:
    """Update or check the docs."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="fail if the docs are out of date"
    )
    args = parser.parse_args()

    pages = sorted(DOCS.glob("*.md"))
    used = {
        m["arg"]
        for p in pages
        for m in _BLOCK.finditer(p.read_text())
        if m["kind"] == "run"
    }
    unknown = used - EXAMPLES.keys()
    if unknown:
        sys.exit(f"ERROR: unknown examples in the docs: {sorted(unknown)}")

    outputs = {}
    for name in sorted(used):
        print(f"running {name}", file=sys.stderr)
        outputs[name] = _run(EXAMPLES[name])

    stale = []
    for page in pages:
        old = page.read_text()
        new = _render(old, outputs)
        if new == old:
            continue
        stale.append(page)
        if args.check:
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

    if args.check and stale:
        print(
            "\nERROR: the docs are out of date, run dev/update_docs.py:",
            *(f"  {p}" for p in stale),
            sep="\n",
            file=sys.stderr,
        )
        return 1

    print(
        f"{'checked' if args.check else 'updated'} {len(pages)} pages", file=sys.stderr
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
