from robot.libraries.BuiltIn import BuiltIn
from robot.api.deco import keyword, not_keyword
from unittest.mock import Mock
from typing import Any, Callable
import importlib

class MockableLibrary:
    """Hybrid library that wraps another library and adds mocking capabilities"""

    def __init__(self, library_name: str):
        self._library_name = library_name
        self._library_instance = None
        self._mocks = {}
        self._original_methods = {}

    @not_keyword
    def _get_library_instance(self):
        if not self._library_instance:
            # Import the actual library
            if '.' in self._library_name:
                module_path, class_name = self._library_name.rsplit('.', 1)
                module = importlib.import_module(module_path)
                lib_class = getattr(module, class_name)
                self._library_instance = lib_class()
            else:
                # Try as module
                self._library_instance = importlib.import_module(self._library_name)
        return self._library_instance

    @not_keyword
    def get_keyword_names(self):
        """Export all keywords from wrapped library + mocking keywords"""
        lib = self._get_library_instance()

        # Get keywords from wrapped library
        if hasattr(lib, 'get_keyword_names'):
            wrapped_keywords = lib.get_keyword_names()
        else:
            wrapped_keywords = [name for name in dir(lib) if not name.startswith('_')]

        # Add mocking keywords
        return wrapped_keywords + ['mock_keyword', 'reset_mocks', 'verify_keyword_called']

    @not_keyword
    def __getattr__(self, name):
        """Proxy all keyword calls to wrapped library or mock"""
        if name in self._mocks:
            return self._mocks[name]

        lib = self._get_library_instance()
        return getattr(lib, name)

    @keyword
    def mock_keyword(self, keyword_name: str, return_value: Any = None, side_effect: Callable = None):
        """Mock a keyword from the wrapped library"""
        lib = self._get_library_instance()
        method_name = keyword_name.lower().replace(' ', '_')

        # Store original if not already mocked
        if method_name not in self._original_methods:
            self._original_methods[method_name] = getattr(lib, method_name)

        # Create mock
        mock = Mock(return_value=return_value, side_effect=side_effect)
        self._mocks[method_name] = mock

        return mock

    @keyword
    def mock_builtin_keyword(self, keyword_name: str, return_value: Any = None):
        """Mock a BuiltIn keyword"""
        builtin = BuiltIn()
        original = builtin.run_keyword

        def patched_run_keyword(name, *args):
            if name.lower().replace(' ', '') == keyword_name.lower().replace(' ', ''):
                return return_value
            return original(name, *args)

        builtin.run_keyword = patched_run_keyword

    @keyword
    def reset_mocks(self):
        """Reset all mocks to original methods"""
        self._mocks.clear()
        self._original_methods.clear()

    @keyword
    def verify_keyword_called(self, keyword_name: str, times: int = None):
        """Verify a mocked keyword was called"""
        method_name = keyword_name.lower().replace(' ', '_')
        if method_name not in self._mocks:
            raise AssertionError(f"Keyword '{keyword_name}' was not mocked")

        mock = self._mocks[method_name]
        if times is not None and mock.call_count != times:
            raise AssertionError(f"Expected {times} calls, got {mock.call_count}")