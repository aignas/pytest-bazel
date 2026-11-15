# pytest-bazel

![standards](https://imgs.xkcd.com/comics/standards.png)

[Documentation] [Changelog] [Contributing]

[documentation]: http://pytest-bazel.readthedocs.io/
[changelog]: ./CHANGELOG.md
[contributing]: ./CONTRIBUTING.md

## Thanks

Special thanks to [rules_python_pytest] and [rules_py] projects that had some
great ideas how to integrate with `pytest`. This attempts to [unify] all of the
approaches.

[rules_python_pytest]: https://github.com/caseyduquettesc/rules_python_pytest 
[rules_py]: https://github.com/aspect-build/rules_py/blob/main/py/private/pytest.py.tmpl
[unify]: https://xkcd.com/927/

## Planned for 1.0

Behaviour changes are added behind opt-in flags first. Their defaults will be
flipped in 1.0. Set them in the `env` of a test, or for all tests with e.g.
`test --test_env=PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE=1` in `.bazelrc`.

| Env var | Default | Default in 1.0 | Description |
| --- | --- | --- | --- |
| `PYTEST_BAZEL_CONSIDER_NAMESPACE_PACKAGES` | `0` | `1` | Pass `-o consider_namespace_packages=true` on pytest 8.1+, so that test modules in packages without `__init__.py` do not shadow third-party packages. |
| `PYTEST_BAZEL_SCOPE_COLLECTION_TO_PACKAGE` | `0` | `1` | Only collect tests from the bazel package of the target when no paths are passed. |
