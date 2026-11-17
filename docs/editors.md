# Editors

Under `bazel test`, the paths in pytest's tracebacks and warnings are relative
to the runfiles root. For the main repository that is the same as the
workspace root, so an editor that runs `bazel test` from the workspace root can
open them:

```text
examples/pkg/test_pkg.py:13:
examples/pkg/helper.py:2: ValueError
```

pytest would print absolute paths into the bazel sandbox, which is gone after
the test, when a test changed the current directory, e.g. with
`monkeypatch.chdir`, and for `--tb=line`. `pytest_bazel` prints those relative
to the runfiles root too. With `bazel run` or without bazel, the paths are the
ones pytest prints.

Files of other repositories, e.g. of pip packages or of the Python standard
library, are printed relative to the runfiles root too, e.g.
`../rules_python++pip+.../site-packages/pkg/mod.py`. Bazel links them in the
`bazel-<workspace>/external/` directory of the workspace, e.g.
`bazel-<workspace>/external/rules_python++pip+.../site-packages/pkg/mod.py`.

The test log of the last run is in `bazel-testlogs/<package>/<target>/test.log`
and has the same paths.

## Neovim and Vim

Load the locations of a run into the quickfix list with `:make`:

```vim
set makeprg=bazel\ test\ --test_output=errors
set errorformat=ERROR:\ %f:%l:%c:\ %m,%f:%l:\ %m,%f:%l:\ ,%-G%.%#
```

Then `:make //pkg:test` runs the test, and
`:cfile bazel-testlogs/pkg/test/test.log` loads the log of the last run. The first
pattern is for the errors of bazel itself, e.g. in a `BUILD.bazel` file. Start
Vim in the workspace root, as the paths are relative to it.

## VS Code

A task in `.vscode/tasks.json` puts the locations in the Problems panel. The
paths are relative to the workspace folder, so it works wherever the terminal
is:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "bazel test",
      "type": "shell",
      "command": "bazel test --test_output=errors //...",
      "group": "test",
      "problemMatcher": {
        "owner": "pytest",
        "fileLocation": ["relative", "${workspaceFolder}"],
        "pattern": {
          "regexp": "^\\s*(\\S+\\.py):(\\d+): (.*)$",
          "file": 1,
          "line": 2,
          "message": 3
        }
      }
    }
  ]
}
```

In the integrated terminal, `Ctrl`+click on a path opens it too, if the
terminal is in the workspace root.
