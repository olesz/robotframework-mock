"""Mock resource for Robot Framework keyword mocking in unit tests."""
# pylint: disable=invalid-name
from typing import Any, Callable
from unittest.mock import Mock

from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn
from robot.running import Return
from robot.running.namespace import Namespace
from robot.utils import split_from_equals

from _mock_core import CallInspectionMixin

# Robot resolves the values of a RETURN statement as variable expressions, so a
# mocked return value cannot be embedded in one directly - anything that is not
# a string raises a TypeError. The value is therefore published under this name
# and the injected RETURN refers to it, which lets a mock return any Python
# object (a query result set, a parsed JSON body, a list of pods...).
RETURN_VARIABLE = '${__mock_resource_return__}'


def _resolve_arguments(keyword_obj, data, context):
    """Split a keyword call's raw arguments into resolved args and kwargs.

    Robot hands the listener the argument list exactly as written at the call
    site, so variables are still unresolved (``${query} commit;``) and named
    arguments are plain ``name=value`` strings. Both are resolved here so that
    mocks record what the keyword was *really* called with, matching what
    ``MockLibrary`` records for library keywords.

    A ``name=value`` item only becomes a named argument when ``name`` is an
    argument the keyword actually declares; otherwise it stays positional, so a
    value that merely contains ``=`` is not misread.

    Args:
        keyword_obj: The keyword being called, used for its argument spec.
        data: Robot keyword call data holding the raw arguments.
        context: Robot execution context, used to resolve variables.

    Returns:
        A ``(args, kwargs)`` tuple of resolved arguments.
    """
    spec = getattr(keyword_obj, 'args', None)
    accepted = set()
    if spec is not None:
        accepted.update(spec.positional or ())
        accepted.update(spec.named_only or ())

    args = []
    kwargs = {}
    for argument in context.variables.replace_list(data.args):
        name, value = (
            split_from_equals(argument) if isinstance(argument, str)
            else (None, None)
        )
        if value is not None and name in accepted:
            kwargs[name] = value
        else:
            args.append(argument)
    return args, kwargs


class MockResource(CallInspectionMixin):
    """Mock keywords from Robot Framework resource files for unit testing.
    
    Example:
        | Library | MockResource | my_resource.robot | WITH NAME | MockRes |
        | MockRes.Mock Keyword | My Keyword | return_value=test_data |
        | My Keyword |
        | MockRes.Reset Mocks |
    """

    def __init__(self, source):
        self._source = source
        self._original_get_runner = Namespace.get_runner
        self._original_items = {}
        self._mocks = {}
        self._install_patch()

    def _install_patch(self):
        original_get_runner = self._original_get_runner
        active_mocks = self._mocks
        source = self._source

        def patched_get_runner(self, keyword_name, recommend_on_failure):
            keyword_runner = original_get_runner(self, keyword_name, recommend_on_failure)
            resource_file = getattr(keyword_runner.keyword, "source", None)

            if source not in str(resource_file):
                return keyword_runner

            mock = active_mocks.get(keyword_name)
            if mock:
                original_run = keyword_runner.run
                def patched_run(data, result, context, run):
                    args, kwargs = _resolve_arguments(
                        keyword_runner.keyword, data, context
                    )
                    mock_result = mock(*args, **kwargs)
                    # Test scope, so the value is visible to the keyword's own
                    # body even when the mocked keyword is called from inside
                    # another keyword rather than directly from the test.
                    context.variables.set_test(RETURN_VARIABLE, mock_result)
                    keyword_runner.keyword.body._items = [Return(values=[RETURN_VARIABLE])]  # pylint: disable=protected-access
                    return original_run(data, result, context, run)
                keyword_runner.run = patched_run

            return keyword_runner

        Namespace.get_runner = patched_get_runner

    @keyword
    def mock_keyword(
        self, keyword_name: str,
        return_value: Any = None, side_effect: Callable = None
    ):
        """Mock a keyword from the resource file.
        
        Args:
            keyword_name: Name of the keyword to mock
            return_value: Value to return when the keyword is called
            side_effect: Callable to execute instead of returning a value.
                Receives the call's resolved arguments, the same way a
                ``MockLibrary`` side effect does.

        Returns:
            The :class:`unittest.mock.Mock` backing the keyword.

        Example:
            | MockRes.Mock Keyword | My Keyword | return_value=test_data |
        """
        keyword_runner = BuiltIn()._namespace.get_runner(keyword_name, True)  # pylint: disable=protected-access
        resource_file = getattr(keyword_runner.keyword, "source", None)

        if self._source not in str(resource_file):
            raise AttributeError("fKeyword '{keyword_name}' not found in {self._source}")

        self._original_items[keyword_name] = keyword_runner.keyword.body._items  # pylint: disable=protected-access
        mock = Mock(return_value=return_value, side_effect=side_effect)
        self._mocks[keyword_name] = mock
        return mock

    @keyword
    def reset_mocks(self):
        """Reset all mocks to their original implementations.
        
        Restores all mocked keywords to their original behavior.
        
        Example:
            | MockRes.Reset Mocks |
        """
        self._mocks.clear()
        for keyword_name, items in self._original_items.items():
            keyword_runner = BuiltIn()._namespace.get_runner(keyword_name, True)  # pylint: disable=protected-access
            keyword_runner.keyword.body._items = items  # pylint: disable=protected-access
        self._original_items.clear()

    @keyword
    def verify_keyword_called(self, keyword_name: str, times: int = None):
        """Verify that a mocked keyword was called.
        
        Args:
            keyword_name: Name of the keyword to verify
            times: Expected number of calls (optional)
        
        Raises:
            AssertionError: If keyword was not mocked or call count doesn't match

        Example:
            | MockDB.Verify Keyword Called | Execute Sql | times=1 |
        """
        if keyword_name not in self._mocks:
            raise AssertionError(f"Keyword '{keyword_name}' was not mocked")

        mock = self._mocks[keyword_name]
        if times is not None and mock.call_count != times:
            raise AssertionError(f"Expected {times} calls, got {mock.call_count}")
