import inspect

from unittest.mock import Mock
from typing import Any, Callable

class MockLibraryWorker(object):
    """Worker class that wraps a library and provides mocking capabilities.
    
    This class acts as a proxy for the wrapped library, intercepting keyword calls
    and returning mocked values when configured. Handles keyword name resolution
    including support for @keyword decorator names.
    """

    def __init__(self, library):
        self._library = library
        self._mocks = {}
        self._original_methods = {}

    def add_mock(self, method_name, mock):
        self._mocks[method_name] = mock

    def reset_mocks(self):
        """Reset all mocks to their original implementations.
        
        Clears all mock configurations and restores original keyword behavior.
        """
        self._mocks.clear()
        self._original_methods.clear()

    def mock_keyword(self, keyword_name: str, return_value: Any = None, side_effect: Callable = None):
        """Mock a keyword from the wrapped library.
        
        Args:
            keyword_name: Name of the keyword to mock (supports both function names and @keyword decorator names)
            return_value: Value to return when the keyword is called (optional)
            side_effect: Callable to execute instead (optional)
            
        Returns:
            Mock object for the keyword
            
        Raises:
            AttributeError: If the keyword is not found in the wrapped library
        """
        lib = self._library
        method_name = keyword_name.lower().replace(' ', '_')

        # Store original if not already mocked
        if method_name not in self._original_methods:
            original_method = None
            try:
                original_method = getattr(lib, method_name)
            except AttributeError:
                for name, method in inspect.getmembers(lib, inspect.ismethod):
                    if hasattr(method, 'robot_name') and method.robot_name.lower() == keyword_name:
                        original_method = name
                        method_name = name
                        break
            if not original_method:
                raise AttributeError(f"Keyword '{keyword_name}' not found in {lib}")
            self._original_methods[method_name] = original_method

        # Create mock
        mock = Mock(return_value=return_value, side_effect=side_effect)
        self._mocks[method_name] = mock

        return mock

    def get_keyword_names(self):
        """Export all keywords from the wrapped library.
        
        Returns:
            List of keyword names available from the wrapped library
        """
        names = []
        for name, kw in inspect.getmembers(self._library):
            if inspect.isfunction(kw) or inspect.ismethod(kw):
                if getattr(kw, "robot_name", None):
                    names.append(kw.robot_name)
                elif name[0] != "_":
                    names.append(name)
        return names

    def verify_keyword_called(self, keyword_name: str, times: int = None):
        """Verify that a mocked keyword was called.
        
        Args:
            keyword_name: Name of the keyword to verify
            times: Expected number of calls (optional, if omitted just verifies it was called)
            
        Raises:
            AssertionError: If the keyword was not mocked or call count doesn't match
        """
        method_name = keyword_name.lower().replace(' ', '_')
        if method_name not in self._mocks:
            raise AssertionError(f"Keyword '{keyword_name}' was not mocked")

        mock = self._mocks[method_name]
        if times is not None and mock.call_count != times:
            raise AssertionError(f"Expected {times} calls, got {mock.call_count}")

#    def run_keyword(self, name, args, kwargs):
#        if name in self._mocks:
#            return self._mocks[name]
#
#        return getattr(self._library, name)

    #@not_keyword
    def __getattr__(self, name):
        """Proxy all keyword calls to wrapped library or mock.
        
        Intercepts attribute access and returns mocked implementation if configured,
        otherwise delegates to the original wrapped library.
        
        Args:
            name: Name of the attribute/keyword being accessed
            
        Returns:
            Mock object if keyword is mocked, otherwise the original keyword from wrapped library
        """
        if name in self._mocks:
            return self._mocks[name]

        return getattr(self._library, name)
