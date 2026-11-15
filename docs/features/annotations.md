# A summary of the results in the test annotations

`pytest_bazel` writes the counts of the outcomes and the failed tests to the
annotations of the test, which bazel adds to
`bazel-testlogs/<target>/test.outputs_manifest/ANNOTATIONS`, so that tools
that read the test outputs can show them.

<!-- source: examples/annotations/test_annotations.py -->
<!-- end -->

<!-- run: annotations -->
<!-- end -->
