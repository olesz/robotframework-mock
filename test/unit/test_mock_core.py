"""Unit tests for the shared call-inspection keywords."""
import unittest
from unittest.mock import Mock

from _mock_core import CallInspectionMixin


class _Host(CallInspectionMixin):
    """Minimal host library keying mocks by the keyword name as written."""

    def __init__(self):
        self._mocks = {}


class _NormalisingHost(CallInspectionMixin):
    """Host library that normalises keyword names into method names."""

    def __init__(self):
        self._mocks = {}

    def _mock_key(self, keyword_name):
        return keyword_name.lower().replace(' ', '_')


class TestCallInspectionMixin(unittest.TestCase):
    """Tests for CallInspectionMixin."""

    def setUp(self):
        """Register a mock that has been called twice."""
        self.host = _Host()
        self.mock = Mock(return_value=None)
        self.host._mocks['Execute Sql'] = self.mock  # pylint: disable=protected-access
        self.mock('SELECT 1', timeout='30')
        self.mock('SELECT 2')

    def test_get_keyword_call_count(self):
        """Call count is taken from the underlying mock."""
        self.assertEqual(self.host.get_keyword_call_count('Execute Sql'), 2)

    def test_get_keyword_call_args(self):
        """Positional arguments of a given call are returned as a list."""
        self.assertEqual(self.host.get_keyword_call_args('Execute Sql'), ['SELECT 1'])
        self.assertEqual(
            self.host.get_keyword_call_args('Execute Sql', index=1), ['SELECT 2']
        )

    def test_get_keyword_call_kwargs(self):
        """Named arguments of a given call are returned as a dict."""
        self.assertEqual(
            self.host.get_keyword_call_kwargs('Execute Sql'), {'timeout': '30'}
        )
        self.assertEqual(self.host.get_keyword_call_kwargs('Execute Sql', index=1), {})

    def test_negative_index_addresses_last_call(self):
        """A negative index counts from the end of the call list."""
        self.assertEqual(
            self.host.get_keyword_call_args('Execute Sql', index=-1), ['SELECT 2']
        )

    def test_index_given_as_string(self):
        """Robot passes arguments as strings, so the index is coerced."""
        self.assertEqual(
            self.host.get_keyword_call_args('Execute Sql', index='1'), ['SELECT 2']
        )

    def test_unmocked_keyword_raises(self):
        """Inspecting a keyword that was never mocked is an error."""
        for inspect in (
            lambda: self.host.get_keyword_call_count('Missing'),
            lambda: self.host.get_keyword_call_args('Missing'),
            lambda: self.host.get_keyword_call_kwargs('Missing'),
            lambda: self.host.verify_keyword_called_with('Missing'),
        ):
            with self.assertRaises(AssertionError) as ctx:
                inspect()
            self.assertIn("was not mocked", str(ctx.exception))

    def test_missing_call_index_raises(self):
        """Asking for a call that was not made reports the actual count."""
        with self.assertRaises(AssertionError) as ctx:
            self.host.get_keyword_call_args('Execute Sql', index=5)
        self.assertIn('No call recorded at index 5', str(ctx.exception))
        self.assertIn('called 2 time(s)', str(ctx.exception))

    def test_verify_keyword_called_with_matches_any_call(self):
        """Verification passes when any recorded call matches."""
        self.host.verify_keyword_called_with('Execute Sql', 'SELECT 1', timeout='30')
        self.host.verify_keyword_called_with('Execute Sql', 'SELECT 2')

    def test_verify_keyword_called_with_mismatch_lists_calls(self):
        """A mismatch reports every recorded call to aid debugging."""
        with self.assertRaises(AssertionError) as ctx:
            self.host.verify_keyword_called_with('Execute Sql', 'SELECT 3')
        message = str(ctx.exception)
        self.assertIn('was not called with', message)
        self.assertIn('SELECT 1', message)
        self.assertIn('SELECT 2', message)

    def test_verify_keyword_called_with_never_called(self):
        """A mock that was never called reports that explicitly."""
        self.host._mocks['Unused'] = Mock()  # pylint: disable=protected-access
        with self.assertRaises(AssertionError) as ctx:
            self.host.verify_keyword_called_with('Unused', 'anything')
        self.assertIn('(never called)', str(ctx.exception))

    def test_mock_key_override_is_used(self):
        """A host that normalises names resolves keywords through _mock_key."""
        host = _NormalisingHost()
        mock = Mock()
        host._mocks['convert_to_binary'] = mock  # pylint: disable=protected-access
        mock('aaa', base='16')

        self.assertEqual(host.get_keyword_call_count('Convert To Binary'), 1)
        self.assertEqual(host.get_keyword_call_args('Convert To Binary'), ['aaa'])
        self.assertEqual(
            host.get_keyword_call_kwargs('Convert To Binary'), {'base': '16'}
        )


if __name__ == '__main__':
    unittest.main()
