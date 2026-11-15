import logging


def test_passes():
    print("not in the XML, the test passes")


def test_fails():
    print("connecting to the database")
    logging.getLogger(__name__).warning("retrying after a timeout")
    assert "connected" == "timed out"


if __name__ == "__main__":
    import pytest_bazel

    pytest_bazel.main()
