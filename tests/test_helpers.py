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

    @patch("tests.helpers.os.name", "nt")
    def test_assert_paths_equal_windows_short_path_fallback(self) -> None:
        # Mock os.path.samefile to simulate a short path match
        with patch("tests.helpers.os.path.samefile") as mock_samefile:
            mock_samefile.return_value = True
            # Even if strings are completely different (like a short path),
            # if samefile returns True, it should not raise AssertionError.
            assert_paths_equal("C:\\DOCUME~1\\TEST", "C:\\Documents and Settings\\TEST")
            mock_samefile.assert_called_once()
