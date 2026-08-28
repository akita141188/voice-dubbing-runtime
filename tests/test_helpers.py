import os
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import assert_paths_equal


class TestHelpers(unittest.TestCase):
    def test_assert_paths_equal_identical(self) -> None:
        assert_paths_equal("foo/bar.txt", "foo/bar.txt")
        assert_paths_equal(Path("foo/bar.txt"), Path("foo/bar.txt"))
        assert_paths_equal(Path("foo/bar.txt"), "foo/bar.txt")

    def test_assert_paths_equal_different_raises(self) -> None:
        with self.assertRaises(AssertionError):
            assert_paths_equal("foo/bar.txt", "foo/baz.txt")

    def test_assert_paths_equal_windows_case_insensitive(self) -> None:
        # On Windows, path casing should not matter
        if os.name == "nt":
            assert_paths_equal("C:\\Foo\\Bar.txt", "c:\\foo\\bar.txt")
            assert_paths_equal(Path("C:\\Foo\\Bar.txt"), Path("c:\\foo\\bar.txt"))

    @unittest.skipUnless(os.name == "nt", "Windows-specific path test")
    @patch("tests.helpers.os.path.samefile", return_value=True)
    def test_assert_paths_equal_windows_short_path_fallback(self, mock_samefile) -> None:
        assert_paths_equal(
            r"C:\DOCUME~1\TEST",
            r"C:\Documents and Settings\TEST",
        )
        mock_samefile.assert_called_once()
