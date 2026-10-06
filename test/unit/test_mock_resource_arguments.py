"""Unit tests for MockResource argument resolution."""
import unittest
from unittest.mock import Mock

from MockResource import _resolve_arguments


class _Spec:
    """Stand-in for Robot's ArgumentSpec."""
    # pylint: disable=too-few-public-methods

    def __init__(self, positional=(), named_only=()):
        self.positional = positional
        self.named_only = named_only


def _call_data(*args):
    data = Mock()
    data.args = args
    return data


def _context(resolved):
    context = Mock()
    context.variables.replace_list.return_value = resolved
    return context


class TestResolveArguments(unittest.TestCase):
    """Tests for _resolve_arguments."""

    def test_variables_are_resolved(self):
        """Arguments are taken from the variable-resolved list, not the raw text."""
        keyword_obj = Mock(args=_Spec(positional=('query',)))
        data = _call_data('${query} commit;')
        context = _context(['SELECT 1 commit;'])

        args, kwargs = _resolve_arguments(keyword_obj, data, context)

        context.variables.replace_list.assert_called_once_with(data.args)
        self.assertEqual(args, ['SELECT 1 commit;'])
        self.assertEqual(kwargs, {})

    def test_declared_named_argument_becomes_kwarg(self):
        """name=value maps to a named argument when the keyword declares it."""
        keyword_obj = Mock(args=_Spec(positional=('arg', 'option')))
        context = _context(['value', 'option=custom'])

        args, kwargs = _resolve_arguments(keyword_obj, _call_data(), context)

        self.assertEqual(args, ['value'])
        self.assertEqual(kwargs, {'option': 'custom'})

    def test_named_only_argument_becomes_kwarg(self):
        """Named-only arguments are accepted as named arguments too."""
        keyword_obj = Mock(args=_Spec(positional=('arg',), named_only=('flag',)))
        context = _context(['value', 'flag=on'])

        args, kwargs = _resolve_arguments(keyword_obj, _call_data(), context)

        self.assertEqual(args, ['value'])
        self.assertEqual(kwargs, {'flag': 'on'})

    def test_undeclared_name_stays_positional(self):
        """A value containing = is not misread as a named argument."""
        keyword_obj = Mock(args=_Spec(positional=('arg',)))
        context = _context(['filter=a=b'])

        args, kwargs = _resolve_arguments(keyword_obj, _call_data(), context)

        self.assertEqual(args, ['filter=a=b'])
        self.assertEqual(kwargs, {})

    def test_non_string_argument_stays_positional(self):
        """A resolved non-string value is passed through untouched."""
        keyword_obj = Mock(args=_Spec(positional=('arg',)))
        payload = {'key': 'value'}
        context = _context([payload])

        args, kwargs = _resolve_arguments(keyword_obj, _call_data(), context)

        self.assertEqual(args, [payload])
        self.assertEqual(kwargs, {})

    def test_missing_argument_spec(self):
        """Without an argument spec every argument stays positional."""
        keyword_obj = Mock(args=None)
        context = _context(['option=custom'])

        args, kwargs = _resolve_arguments(keyword_obj, _call_data(), context)

        self.assertEqual(args, ['option=custom'])
        self.assertEqual(kwargs, {})


if __name__ == '__main__':
    unittest.main()
