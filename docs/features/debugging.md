# Debugging tests

`bazel test` runs a test without a terminal, so a debugger cannot read what
you type and would quit right away. `pytest_bazel` fails with a message
instead, both for `breakpoint()` and for `--pdb` and `--trace`:

<!-- source: examples/debugging/test_debugging.py -->
```{code-block} python
:caption: examples/debugging/test_debugging.py

def test_add():
    total = 1 + 1
    breakpoint()
    assert total == 3


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
```
<!-- end -->

<!-- run: debugging_breakpoint -->
```console
$ bazel test //examples/debugging:debugging_test
//examples/debugging:debugging_test FAILED in <time>
$ cat bazel-testlogs/examples/debugging/debugging_test/test.log
E       RuntimeError: breakpoint() was called. bazel test gives the test no terminal to debug it in. Run it with `bazel run //examples/debugging:debugging_test -- --pdb` instead.
examples/debugging/test_debugging.py:3: RuntimeError
FAILED examples/debugging/test_debugging.py::test_add - RuntimeError: breakpo...
============================== 1 failed in <time> ===============================
```
<!-- end -->

<!-- run: debugging_pdb -->
```console
$ bazel test //examples/debugging:debugging_test --test_arg=--pdb
//examples/debugging:debugging_test FAILED in <time>
$ cat bazel-testlogs/examples/debugging/debugging_test/test.log
ERROR: --pdb needs a terminal. bazel test gives the test no terminal to debug it in. Run it with `bazel run //examples/debugging:debugging_test -- --pdb` instead.
```
<!-- end -->

To debug, run the test with `bazel run`, which gives it the terminal. The
args after `--` are passed to pytest, e.g. to stop at the first failure and
only run one test:

```console
$ bazel run //examples/debugging:debugging_test -- --pdb -k test_add
...
>>>>>>>>>>>>>>>>>>>> PDB set_trace (IO-capturing turned off) >>>>>>>>>>>>>>>>>>>>
> <runfiles>/_main/examples/debugging/test_debugging.py(4)test_add()
-> assert total == 3
(Pdb) p total
2
```

`bazel run` sets up the same environment for the test as `bazel test`, but
keeps the terminal.
