"""Unit tests for MockResource."""
import unittest
from unittest.mock import Mock, patch
from MockResource import MockResource


class TestMockResource(unittest.TestCase):
    """Tests for MockResource class."""

    def setUp(self):
        """Set up test fixtures."""
        self.source = "test_resource.robot"
        self.mock_resource = MockResource(self.source)

    def tearDown(self):
        """Clean up after tests."""
        # Manually clear state without calling reset_mocks to avoid Robot context issues
        self.mock_resource._mocks.clear()  # pylint: disable=protected-access
        self.mock_resource._original_items.clear()  # pylint: disable=protected-access

    def test_init(self):
        """Test initialization stores source and sets up internal state."""
        mock_resource = MockResource("test.robot")
        self.assertEqual(mock_resource._source, "test.robot")  # pylint: disable=protected-access
        self.assertIsNotNone(mock_resource._original_get_runner)  # pylint: disable=protected-access
        self.assertEqual(len(mock_resource._original_items), 0)  # pylint: disable=protected-access
        self.assertEqual(len(mock_resource._mocks), 0)  # pylint: disable=protected-access

    @patch('MockResource.BuiltIn')
    def test_mock_keyword_success(self, mock_builtin):
        """Test mocking a keyword successfully."""
        keyword_runner = Mock()
        keyword_runner.keyword.source = self.source
        keyword_runner.keyword.body._items = ["original_item"]  # pylint: disable=protected-access
        mock_builtin.return_value._namespace.get_runner.return_value = keyword_runner  # pylint: disable=protected-access

        self.mock_resource.mock_keyword("Test Keyword", return_value="mocked")

        self.assertIn("Test Keyword", self.mock_resource._mocks)  # pylint: disable=protected-access
        self.assertIn("Test Keyword", self.mock_resource._original_items)  # pylint: disable=protected-access

    @patch('MockResource.BuiltIn')
    def test_mock_keyword_wrong_source(self, mock_builtin):
        """Test mocking a keyword from wrong source raises AttributeError."""
        keyword_runner = Mock()
        keyword_runner.keyword.source = "different_resource.robot"
        mock_builtin.return_value._namespace.get_runner.return_value = keyword_runner  # pylint: disable=protected-access

        with self.assertRaises(AttributeError):
            self.mock_resource.mock_keyword("Test Keyword")

    @patch('MockResource.BuiltIn')
    def test_mock_keyword_with_side_effect(self, mock_builtin):
        """Test mocking a keyword with side effect."""
        keyword_runner = Mock()
        keyword_runner.keyword.source = self.source
        keyword_runner.keyword.body._items = ["original_item"]  # pylint: disable=protected-access
        mock_builtin.return_value._namespace.get_runner.return_value = keyword_runner  # pylint: disable=protected-access

        def side_effect(_args):
            return "side_effect_result"

        self.mock_resource.mock_keyword("Test Keyword", side_effect=side_effect)

        mock = self.mock_resource._mocks["Test Keyword"]  # pylint: disable=protected-access
        self.assertEqual(mock.side_effect, side_effect)

    @patch('MockResource.BuiltIn')
    def test_reset_mocks(self, mock_builtin):
        """Test resetting mocks clears state and restores original items."""
        keyword_runner = Mock()
        keyword_runner.keyword.source = self.source
        keyword_runner.keyword.body._items = ["original_item"]  # pylint: disable=protected-access
        mock_builtin.return_value._namespace.get_runner.return_value = keyword_runner  # pylint: disable=protected-access

        self.mock_resource.mock_keyword("Test Keyword", return_value="mocked")
        self.assertEqual(len(self.mock_resource._mocks), 1)  # pylint: disable=protected-access

        # Mock the get_runner call in reset_mocks
        mock_builtin.return_value._namespace.get_runner.return_value = keyword_runner  # pylint: disable=protected-access
        self.mock_resource.reset_mocks()

        self.assertEqual(len(self.mock_resource._mocks), 0)  # pylint: disable=protected-access
        self.assertEqual(len(self.mock_resource._original_items), 0)  # pylint: disable=protected-access
        self.assertEqual(keyword_runner.keyword.body._items, ["original_item"])  # pylint: disable=protected-access

    def test_verify_keyword_called(self):
        """Test verifying a keyword was called."""
        mock = Mock()
        self.mock_resource._mocks["Test Keyword"] = mock  # pylint: disable=protected-access
        mock()

        self.mock_resource.verify_keyword_called("Test Keyword")

    def test_verify_keyword_called_with_times(self):
        """Test verifying a keyword was called specific number of times."""
        mock = Mock()
        self.mock_resource._mocks["Test Keyword"] = mock  # pylint: disable=protected-access
        mock()
        mock()

        self.mock_resource.verify_keyword_called("Test Keyword", times=2)

    def test_verify_keyword_called_wrong_times(self):
        """Test verifying with wrong call count raises AssertionError."""
        mock = Mock()
        self.mock_resource._mocks["Test Keyword"] = mock  # pylint: disable=protected-access
        mock()

        with self.assertRaises(AssertionError) as ctx:
            self.mock_resource.verify_keyword_called("Test Keyword", times=2)
        self.assertIn("Expected 2 calls, got 1", str(ctx.exception))

    def test_verify_keyword_not_mocked(self):
        """Test verifying a non-mocked keyword raises AssertionError."""
        with self.assertRaises(AssertionError) as ctx:
            self.mock_resource.verify_keyword_called("Test Keyword")
        self.assertIn("was not mocked", str(ctx.exception))

    def test_verify_keyword_called_zero_times(self):
        """Test verifying a keyword was called zero times."""
        mock = Mock()
        self.mock_resource._mocks["Test Keyword"] = mock  # pylint: disable=protected-access

        self.mock_resource.verify_keyword_called("Test Keyword", times=0)

    @patch('MockResource.BuiltIn')
    def test_mock_multiple_keywords(self, mock_builtin):
        """Test mocking multiple keywords."""
        keyword_runner1 = Mock()
        keyword_runner1.keyword.source = self.source
        keyword_runner1.keyword.body._items = ["item1"]  # pylint: disable=protected-access

        keyword_runner2 = Mock()
        keyword_runner2.keyword.source = self.source
        keyword_runner2.keyword.body._items = ["item2"]  # pylint: disable=protected-access

        mock_builtin.return_value._namespace.get_runner.side_effect = [  # pylint: disable=protected-access
            keyword_runner1, keyword_runner2
        ]

        self.mock_resource.mock_keyword("Keyword One", return_value="mock1")
        self.mock_resource.mock_keyword("Keyword Two", return_value="mock2")

        self.assertEqual(len(self.mock_resource._mocks), 2)  # pylint: disable=protected-access
        self.assertIn("Keyword One", self.mock_resource._mocks)  # pylint: disable=protected-access
        self.assertIn("Keyword Two", self.mock_resource._mocks)  # pylint: disable=protected-access


if __name__ == '__main__':
    unittest.main()
