from pathlib import Path
import unittest


def test_tmpdir(tmpdir):
    tmp_file = Path(tmpdir) / "foo.txt"
    want = "42"
    tmp_file.write_text(want)
    got = tmp_file.read_text()
    assert want == got


class TestCase(unittest.TestCase):
    def test_simple(self):
        self.assertEqual("42", "42")
