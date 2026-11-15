---
# The examples that dev/update_docs runs for the `run` blocks below.
pytest_bazel_examples:
  annotations:
    target: '//examples/annotations:annotations_test'
    files: ['test.outputs_manifest/ANNOTATIONS']
---

# A summary of the results in the test annotations

`pytest_bazel` writes the counts of the outcomes and the failed tests to the
annotations of the test, which bazel adds to
`bazel-testlogs/<target>/test.outputs_manifest/ANNOTATIONS`, so that tools
that read the test outputs can show them.

<!-- source: examples/annotations/test_annotations.py -->
```{code-block} python
:caption: examples/annotations/test_annotations.py

import pytest


def test_passes():
    pass


def test_fails():
    assert 1 + 1 == 3


@pytest.mark.skip(reason="not today")
def test_skipped():
    pass


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- run: annotations -->
```console
$ bazel test //examples/annotations:annotations_test
//examples/annotations:annotations_test FAILED in <time>
$ cat bazel-testlogs/examples/annotations/annotations_test/test.outputs_manifest/ANNOTATIONS
pytest: 1 failed, 1 passed, 1 skipped
FAILED examples/annotations/test_annotations.py::test_fails
```
<!-- end -->
