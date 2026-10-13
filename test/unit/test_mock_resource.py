"""Unit tests for MockResource."""
import unittest
from unittest.mock import Mock, patch
import MockResource as MockResource_module
from MockResource import MockResource
from _mock_core import normalize_keyword_name


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
        self.mock_resource._original_setups.clear()  # pylint: disable=protected-access
        self.mock_resource._original_teardowns.clear()  # pylint: disable=protected-access
        self.mock_resource._mocked_sources.clear()  # pylint: disable=protected-access
        self.mock_resource._mocked_names.clear()  # pylint: disable=protected-access

    def _runner(self, items=None, setup=None, teardown=None):
        """Return a stub keyword runner for this instance's source.

        Args:
            items: Body items the keyword starts with.
            setup: The keyword's ``[Setup]``.
            teardown: The keyword's ``[Teardown]``.

        Returns:
            A ``Mock`` shaped like a Robot keyword runner.
        """
        keyword_runner = Mock()
        keyword_runner.keyword.source = self.source
        keyword_runner.keyword.body._items = ["original_item"] if items is None else items  # pylint: disable=protected-access
        keyword_runner.keyword.setup = setup
        keyword_runner.keyword.teardown = teardown
        return keyword_runner

    def test_init(self):
        """Test initialization stores source and sets up internal state."""
        mock_resource = MockResource("test.robot")
        self.assertEqual(mock_resource._source, "test.robot")  # pylint: disable=protected-access
        self.assertIsNotNone(MockResource_module._ORIGINAL_GET_RUNNER)  # pylint: disable=protected-access
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

        self.assertIn(normalize_keyword_name("Test Keyword"), self.mock_resource._mocks)  # pylint: disable=protected-access
        self.assertIn(normalize_keyword_name("Test Keyword"), self.mock_resource._original_items)  # pylint: disable=protected-access

    @patch('MockResource.BuiltIn')
    def test_mock_keyword_wrong_source(self, mock_builtin):
        """Test mocking a keyword from wrong source raises AttributeError."""
        keyword_runner = Mock()
        keyword_runner.keyword.source = "different_resource.robot"
        mock_builtin.return_value._namespace.get_runner.return_value = keyword_runner  # pylint: disable=protected-access

        with self.assertRaises(AttributeError):
            self.mock_resource.mock_keyword("Test Keyword")

    @patch('MockResource.BuiltIn')
    def test_mock_keyword_wrong_source_message(self, mock_builtin):
        """Test the error names the keyword and the searched source.

        This message is the only diagnostic when a mock target cannot be
        resolved, so it has to identify both halves of the lookup.
        """
        keyword_runner = Mock()
        keyword_runner.keyword.source = "different_resource.robot"
        mock_builtin.return_value._namespace.get_runner.return_value = keyword_runner  # pylint: disable=protected-access

        with self.assertRaises(AttributeError) as ctx:
            self.mock_resource.mock_keyword("Test Keyword")

        message = str(ctx.exception)
        self.assertIn("Test Keyword", message)
        self.assertIn(self.source, message)
        self.assertNotIn("{", message)
        self.assertFalse(message.startswith("f"))

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

        mock = self.mock_resource._mocks[normalize_keyword_name("Test Keyword")]  # pylint: disable=protected-access
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
        self.mock_resource._mocks[normalize_keyword_name("Test Keyword")] = mock  # pylint: disable=protected-access
        mock()

        self.mock_resource.verify_keyword_called("Test Keyword")

    def test_verify_keyword_called_with_times(self):
        """Test verifying a keyword was called specific number of times."""
        mock = Mock()
        self.mock_resource._mocks[normalize_keyword_name("Test Keyword")] = mock  # pylint: disable=protected-access
        mock()
        mock()

        self.mock_resource.verify_keyword_called("Test Keyword", times=2)

    def test_verify_keyword_called_wrong_times(self):
        """Test verifying with wrong call count raises AssertionError."""
        mock = Mock()
        self.mock_resource._mocks[normalize_keyword_name("Test Keyword")] = mock  # pylint: disable=protected-access
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
        self.mock_resource._mocks[normalize_keyword_name("Test Keyword")] = mock  # pylint: disable=protected-access

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
        self.assertIn(normalize_keyword_name("Keyword One"), self.mock_resource._mocks)  # pylint: disable=protected-access
        self.assertIn(normalize_keyword_name("Keyword Two"), self.mock_resource._mocks)  # pylint: disable=protected-access

    @patch('MockResource.BuiltIn')
    def test_mock_same_keyword_twice(self, mock_builtin):
        """Test mocking the same keyword twice replaces the mock."""
        keyword_runner = self._runner()
        mock_builtin.return_value._namespace.get_runner.return_value = keyword_runner  # pylint: disable=protected-access

        self.mock_resource.mock_keyword("Test Keyword", return_value="first")
        self.mock_resource.mock_keyword("Test Keyword", return_value="second")

        key = normalize_keyword_name("Test Keyword")
        self.assertEqual(len(self.mock_resource._mocks), 1)  # pylint: disable=protected-access
        self.assertEqual(self.mock_resource._mocks[key].return_value, "second")  # pylint: disable=protected-access

    @patch('MockResource.BuiltIn')
    def test_remock_keeps_the_first_saved_body(self, mock_builtin):
        """Test re-mocking does not overwrite the saved original body.

        Calling a mocked keyword replaces its body with the injected RETURN, so
        a second mock that saved the body again would make reset restore the
        mock instead of the real keyword - permanently, since resource keyword
        objects are shared for the whole run.
        """
        keyword_runner = self._runner()
        mock_builtin.return_value._namespace.get_runner.return_value = keyword_runner  # pylint: disable=protected-access

        self.mock_resource.mock_keyword("Test Keyword", return_value="first")
        # The injected RETURN the patched runner installs on the first call.
        keyword_runner.keyword.body._items = ["mocked_return_item"]  # pylint: disable=protected-access
        self.mock_resource.mock_keyword("Test Keyword", return_value="second")
        self.mock_resource.reset_mocks()

        self.assertEqual(keyword_runner.keyword.body._items, ["original_item"])  # pylint: disable=protected-access

    @patch('MockResource.BuiltIn')
    def test_remock_under_a_different_spelling_is_one_entry(self, mock_builtin):
        """Test a differently spelled name is the same keyword.

        Robot matches keyword names ignoring case, spaces and underscores, so
        two spellings must not each save their own "original".
        """
        keyword_runner = self._runner()
        mock_builtin.return_value._namespace.get_runner.return_value = keyword_runner  # pylint: disable=protected-access

        self.mock_resource.mock_keyword("Test Keyword", return_value="first")
        keyword_runner.keyword.body._items = ["mocked_return_item"]  # pylint: disable=protected-access
        self.mock_resource.mock_keyword("test_keyword", return_value="second")

        self.assertEqual(len(self.mock_resource._original_items), 1)  # pylint: disable=protected-access
        self.mock_resource.reset_mocks()
        self.assertEqual(keyword_runner.keyword.body._items, ["original_item"])  # pylint: disable=protected-access

    @patch('MockResource.BuiltIn')
    def test_remock_with_skip_teardown_twice_restores_the_teardown(self, mock_builtin):
        """Test the suppressed teardown survives being mocked twice."""
        keyword_runner = self._runner(teardown="real_teardown")
        mock_builtin.return_value._namespace.get_runner.return_value = keyword_runner  # pylint: disable=protected-access

        self.mock_resource.mock_keyword("Test Keyword", skip_teardown=True)
        self.mock_resource.mock_keyword("Test Keyword", skip_teardown=True)
        self.assertIsNone(keyword_runner.keyword.teardown)

        self.mock_resource.reset_mocks()

        self.assertEqual(keyword_runner.keyword.teardown, "real_teardown")

    @patch('MockResource.BuiltIn')
    def test_remock_without_skip_teardown_puts_the_teardown_back(self, mock_builtin):
        """Test dropping skip_teardown on a re-mock re-enables the teardown.

        The argument says whether the teardown runs, so it has to take effect on
        every call rather than only on the first.
        """
        keyword_runner = self._runner(teardown="real_teardown")
        mock_builtin.return_value._namespace.get_runner.return_value = keyword_runner  # pylint: disable=protected-access

        self.mock_resource.mock_keyword("Test Keyword", skip_teardown=True)
        self.mock_resource.mock_keyword("Test Keyword")

        self.assertEqual(keyword_runner.keyword.teardown, "real_teardown")

    @patch('MockResource.BuiltIn')
    def test_remock_without_skip_setup_puts_the_setup_back(self, mock_builtin):
        """Test dropping skip_setup on a re-mock re-enables the setup."""
        keyword_runner = self._runner(setup="real_setup")
        mock_builtin.return_value._namespace.get_runner.return_value = keyword_runner  # pylint: disable=protected-access

        self.mock_resource.mock_keyword("Test Keyword", skip_setup=True)
        self.mock_resource.mock_keyword("Test Keyword")

        self.assertEqual(keyword_runner.keyword.setup, "real_setup")


if __name__ == '__main__':
    unittest.main()
