---
# The examples that dev/update_docs runs for the `run` blocks below.
pytest_bazel_examples:
  namespace_packages_off:
    target: '//examples/namespace_packages:off_test'
    keep: 'module name'
  namespace_packages:
    target: '//examples/namespace_packages:namespace_packages_test'
    keep: 'module name'
---

# Module names in packages without `__init__.py`

On by default since 1.0, set `PYTEST_BAZEL_CONSIDER_NAMESPACE_PACKAGES=0` to
turn it off. Bazel packages often have no `__init__.py`, so pytest names the
test module after the closest regular package only. Here that is `numpy`, which
then shadows the real `numpy` for the code under test.

<!-- source: examples/namespace_packages/numpy/test_module_name.py -->
```{code-block} python
:caption: examples/namespace_packages/numpy/test_module_name.py

def test_module_name():
    print("module name:", __name__)
```
<!-- end -->

With `PYTEST_BAZEL_CONSIDER_NAMESPACE_PACKAGES=0`, as before 1.0:

<!-- run: namespace_packages_off -->
```console
$ bazel test //examples/namespace_packages:off_test
//examples/namespace_packages:off_test PASSED in <time>
$ cat bazel-testlogs/examples/namespace_packages/off_test/test.log
examples/namespace_packages/numpy/test_module_name.py module name: numpy.test_module_name
```
<!-- end -->

By default:

<!-- run: namespace_packages -->
```console
$ bazel test //examples/namespace_packages:namespace_packages_test
//examples/namespace_packages:namespace_packages_test PASSED in <time>
$ cat bazel-testlogs/examples/namespace_packages/namespace_packages_test/test.log
examples/namespace_packages/numpy/test_module_name.py module name: examples.namespace_packages.numpy.test_module_name
```
<!-- end -->
