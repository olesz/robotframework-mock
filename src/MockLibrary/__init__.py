"""Mock library for Robot Framework keyword mocking in unit tests."""
# pylint: disable=invalid-name
import inspect
from typing import Any, Callable
from unittest.mock import Mock
from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn

__version__ = "1.0.0"


def _get_library_instance(library_name_or_alias):
    lib = BuiltIn().get_library_instance(library_name_or_alias)
    if not lib:
        raise RuntimeError(
            f"Library with name {library_name_or_alias} is not found "
            f"in robot. Import it first!"
        )
    return lib


class MockLibrary():
    """Mock keywords from any Robot Framework library for unit testing.
    
    Example:
        | Library | DatabaseLibrary |
        | Library | MockLibrary | DatabaseLibrary | WITH NAME | MockDB |
        | MockDB.Mock Keyword | query | return_value=test_data |
        | ${result}= | DatabaseLibrary.Query | SELECT * FROM users |
        | Should Be Equal | ${result} | test_data |
        | MockDB.Reset Mocks |
    """

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, library_name_or_alias: str, lib: Any = None):
        self._original_methods = {}
        self._mocks = {}
        if lib:
            self._library_instance = lib
        else:
            self._library_instance = _get_library_instance(library_name_or_alias)

    @keyword
    def mock_keyword(
        self, keyword_name: str,
        return_value: Any = None, side_effect: Callable = None
    ):
        """Mock a keyword from the wrapped library.
        
        Example:
            | MockDB.Mock Keyword | query | return_value=test_data |
        """
        lib = self._library_instance
        method_name = keyword_name.lower().replace(' ', '_')

        if method_name not in self._original_methods:
            original_method = None
            try:
                original_method = getattr(lib, method_name)
            except AttributeError:
                for name, method in inspect.getmembers(
                    lib, inspect.ismethod
                ):
                    if (hasattr(method, 'robot_name') and
                            method.robot_name.lower() == keyword_name):
                        original_method = getattr(lib, name)
                        method_name = name
                        break
            if not original_method:
                raise AttributeError(f"Keyword '{keyword_name}' not found in {lib}")
            self._original_methods[method_name] = original_method

        mock = Mock(return_value=return_value, side_effect=side_effect)
        self._mocks[method_name] = mock

        try:
            owner_class = self._original_methods[method_name].__self__.__class__
            setattr(owner_class, method_name, mock)
        except AttributeError:
            setattr(lib, method_name, mock)


        return mock

    @keyword
    def reset_mocks(self):
        """Reset all mocks to their original implementations.
        
        Example:
            | MockDB.Reset Mocks |
        """
        for method_name, original_method in self._original_methods.items():
            try:
                owner_class = original_method.__self__.__class__
                setattr(owner_class, method_name, original_method)
            except AttributeError:
                setattr(self._library_instance, method_name, original_method)

        self._mocks.clear()
        self._original_methods.clear()

    @keyword
    def verify_keyword_called(self, keyword_name: str, times: int = None):
        """Verify that a mocked keyword was called.
        
        Example:
            | MockDB.Verify Keyword Called | execute_sql | times=1 |
        """
        method_name = keyword_name.lower().replace(' ', '_')
        if method_name not in self._mocks:
            raise AssertionError(f"Keyword '{keyword_name}' was not mocked")

        mock = self._mocks[method_name]
        if times is not None and mock.call_count != times:
            raise AssertionError(f"Expected {times} calls, got {mock.call_count}")
