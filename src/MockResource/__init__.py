"""Mock resource for Robot Framework keyword mocking in unit tests."""
# pylint: disable=invalid-name
from typing import Any, Callable
from unittest.mock import Mock

from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn
from robot.running import Return
from robot.running.namespace import Namespace


class MockResource:
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
                    mock_result = mock(data.args)
                    keyword_runner.keyword.body._items = [Return(values=[mock_result])]  # pylint: disable=protected-access
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
            side_effect: Callable to execute instead of returning a value
        
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
