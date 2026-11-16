"""Run the pytest bazel wrapper."""

import sys

from pytest_bazel._impl.main import main

sys.exit(main())
