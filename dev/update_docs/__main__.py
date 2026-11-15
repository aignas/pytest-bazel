"""Update the generated parts of docs/features/*.md by running the examples.

The docs contain blocks between markers that this script fills in:

    <!-- source: examples/test_filter/test_filter.py -->
    ...the contents of the file...
    <!-- end -->

    <!-- run: test_filter -->
    ...the bazel command of the example and its output...
    <!-- end -->

Each page defines the examples of its `run` blocks in its frontmatter, see
`lib.FRONTMATTER`, so that new features do not conflict.

Usage:

    bazel run //dev/update_docs            # update the docs
    bazel run //dev/update_docs -- --check # fail if the docs are out of date
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# The directory of this file is on sys.path, see BUILD.bazel.
from lib import DOCS, DocsError, Example, examples_of, run, update, used_examples


def load(pages: list[Path]) -> dict[Path, dict[str, Example]]:
    """Return the examples that the `run` blocks of each page need."""
    needed = {}
    for page in pages:
        text = page.read_text()
        examples = examples_of(text, page)
        used = used_examples(text)
        unknown = sorted(set(used) - examples.keys())
        if unknown:
            msg = (
                f"{page}: the `run` blocks {unknown} have no example in the frontmatter"
            )
            raise DocsError(msg)
        unused = sorted(examples.keys() - set(used))
        if unused:
            msg = f"{page}: the examples {unused} have no `run` block"
            raise DocsError(msg)
        needed[page] = {name: examples[name] for name in used}
    return needed


def main(argv: Optional[list[str]] = None) -> int:
    """Update or check the docs."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="fail if the docs are out of date"
    )
    args = parser.parse_args(argv)

    # `bazel run` starts the script in its runfiles, the docs are in the
    # workspace.
    workspace = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace:
        os.chdir(workspace)

    pages = sorted(DOCS.glob("*.md"))
    try:
        needed = load(pages)
    except DocsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    outputs = {}
    for page, examples in needed.items():
        outputs[page] = {}
        for name, example in examples.items():
            print(f"running {name}", file=sys.stderr)
            outputs[page][name] = run(example)

    stale = update(pages, outputs, check=args.check)
    if args.check and stale:
        print(
            "\nERROR: the docs are out of date, run `bazel run //dev/update_docs`:",
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
