import warnings


def check(value):
    assert value == 42, "helper failed"  # noqa: PLR2004


def warn():
    warnings.warn("a helper warning", UserWarning, stacklevel=1)
