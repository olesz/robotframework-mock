"""Unit tests for MockLibrary."""
import unittest
from unittest.mock import Mock, patch
from robot.api.deco import keyword
from MockLibrary import MockLibrary, _get_library_instance


class SampleLibrary:
    """Sample library for testing."""

    def simple_keyword(self):
        """Return original value."""
        return "original"

    def another_keyword(self, arg):
        """Return original value with arg."""
        return f"original_{arg}"

    @keyword(name="Custom Name")
    def custom_named_keyword(self):
        """Return custom value."""
        return "custom"


class TestGetLibraryInstance(unittest.TestCase):
    """Tests for _get_library_instance function."""

    @patch('MockLibrary.BuiltIn')
    def test_get_existing_library(self, mock_builtin):
        """Test getting an existing library instance."""
        lib = Mock()
        mock_builtin.return_value.get_library_instance.return_value = lib
        result = _get_library_instance("TestLib")
        self.assertEqual(result, lib)

    @patch('MockLibrary.BuiltIn')
    def test_get_nonexistent_library(self, mock_builtin):
        """Test getting a non-existent library raises RuntimeError."""
        mock_builtin.return_value.get_library_instance.return_value = None
        with self.assertRaises(RuntimeError) as ctx:
            _get_library_instance("NonExistent")
        self.assertIn("NonExistent", str(ctx.exception))


class TestMockLibrary(unittest.TestCase):
    """Tests for MockLibrary class."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_lib = SampleLibrary()
        self.mock_lib = MockLibrary("TestLib", lib=self.sample_lib)

    def tearDown(self):
        """Clean up after tests."""
        self.mock_lib.reset_mocks()

    def test_init_with_lib(self):
        """Test initialization with a library instance."""
        mock_lib = MockLibrary("TestLib", lib=self.sample_lib)
        self.assertEqual(mock_lib._library_instance, self.sample_lib)  # pylint: disable=protected-access

    @patch('MockLibrary._get_library_instance')
    def test_init_without_lib(self, mock_get_lib):
        """Test initialization without a library instance."""
        lib = Mock()
        mock_get_lib.return_value = lib
        mock_lib = MockLibrary("TestLib")
        self.assertEqual(mock_lib._library_instance, lib)  # pylint: disable=protected-access

    def test_mock_keyword_simple(self):
        """Test mocking a simple keyword."""
        self.mock_lib.mock_keyword("simple_keyword", return_value="mocked")
        result = self.sample_lib.simple_keyword()
        self.assertEqual(result, "mocked")

    def test_mock_keyword_with_spaces(self):
        """Test mocking a keyword with spaces in the name."""
        self.mock_lib.mock_keyword("simple keyword", return_value="mocked")
        result = self.sample_lib.simple_keyword()
        self.assertEqual(result, "mocked")

    def test_mock_keyword_side_effect(self):
        """Test mocking a keyword with a side effect."""
        def side_effect(*_args, **_kwargs):
            return "side_effect_result"
        self.mock_lib.mock_keyword("simple_keyword", side_effect=side_effect)
        result = self.sample_lib.simple_keyword()
        self.assertEqual(result, "side_effect_result")

    def test_mock_keyword_with_args(self):
        """Test mocking a keyword that takes arguments."""
        self.mock_lib.mock_keyword("another_keyword", return_value="mocked_value")
        result = self.sample_lib.another_keyword("test")
        self.assertEqual(result, "mocked_value")

    def test_mock_keyword_returns_mock(self):
        """Test that mock_keyword returns a Mock object."""
        mock = self.mock_lib.mock_keyword("simple_keyword", return_value="test")
        self.assertIsInstance(mock, Mock)

    def test_mock_same_keyword_twice(self):
        """Test mocking the same keyword twice updates the mock."""
        self.mock_lib.mock_keyword("simple_keyword", return_value="first")
        self.mock_lib.mock_keyword("simple_keyword", return_value="second")
        result = self.sample_lib.simple_keyword()
        self.assertEqual(result, "second")

    def test_mock_keyword_not_found(self):
        """Test mocking a non-existent keyword raises AttributeError."""
        with self.assertRaises(AttributeError) as ctx:
            self.mock_lib.mock_keyword("nonexistent_keyword")
        self.assertIn("nonexistent_keyword", str(ctx.exception))

    def test_reset_mocks(self):
        """Test resetting mocks restores original behavior."""
        self.mock_lib.mock_keyword("simple_keyword", return_value="mocked")
        self.assertEqual(self.sample_lib.simple_keyword(), "mocked")
        self.mock_lib.reset_mocks()
        self.assertEqual(self.sample_lib.simple_keyword(), "original")

    def test_reset_mocks_clears_internal_state(self):
        """Test that reset_mocks clears internal state."""
        self.mock_lib.mock_keyword("simple_keyword", return_value="mocked")
        self.mock_lib.reset_mocks()
        self.assertEqual(len(self.mock_lib._mocks), 0)  # pylint: disable=protected-access
        self.assertEqual(len(self.mock_lib._original_methods), 0)  # pylint: disable=protected-access

    def test_reset_mocks_multiple_keywords(self):
        """Test resetting multiple mocked keywords."""
        self.mock_lib.mock_keyword("simple_keyword", return_value="mocked1")
        self.mock_lib.mock_keyword("another_keyword", return_value="mocked2")
        self.mock_lib.reset_mocks()
        self.assertEqual(self.sample_lib.simple_keyword(), "original")
        self.assertEqual(self.sample_lib.another_keyword("x"), "original_x")

    def test_verify_keyword_called(self):
        """Test verifying a keyword was called."""
        self.mock_lib.mock_keyword("simple_keyword", return_value="mocked")
        self.sample_lib.simple_keyword()
        self.mock_lib.verify_keyword_called("simple_keyword")

    def test_verify_keyword_called_with_times(self):
        """Test verifying a keyword was called a specific number of times."""
        self.mock_lib.mock_keyword("simple_keyword", return_value="mocked")
        self.sample_lib.simple_keyword()
        self.sample_lib.simple_keyword()
        self.mock_lib.verify_keyword_called("simple_keyword", times=2)

    def test_verify_keyword_called_wrong_times(self):
        """Test verifying with wrong call count raises AssertionError."""
        self.mock_lib.mock_keyword("simple_keyword", return_value="mocked")
        self.sample_lib.simple_keyword()
        with self.assertRaises(AssertionError) as ctx:
            self.mock_lib.verify_keyword_called("simple_keyword", times=2)
        self.assertIn("Expected 2 calls, got 1", str(ctx.exception))

    def test_verify_keyword_not_mocked(self):
        """Test verifying a non-mocked keyword raises AssertionError."""
        with self.assertRaises(AssertionError) as ctx:
            self.mock_lib.verify_keyword_called("simple_keyword")
        self.assertIn("was not mocked", str(ctx.exception))

    def test_verify_keyword_called_zero_times(self):
        """Test verifying a keyword was called zero times."""
        self.mock_lib.mock_keyword("simple_keyword", return_value="mocked")
        self.mock_lib.verify_keyword_called("simple_keyword", times=0)

    def test_verify_keyword_with_spaces(self):
        """Test verifying a keyword with spaces in the name."""
        self.mock_lib.mock_keyword("simple keyword", return_value="mocked")
        self.sample_lib.simple_keyword()
        self.mock_lib.verify_keyword_called("simple keyword", times=1)


if __name__ == '__main__':
    unittest.main()
