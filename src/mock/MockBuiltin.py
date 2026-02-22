import inspect

from unittest.mock import Mock
from robot.api.deco import keyword, not_keyword
from robot.libraries.BuiltIn import BuiltIn
from typing import Any, Callable


class MockBuiltin:
    """A Robot Framework library for mocking BuiltIn library keywords.
    
    Uses a singleton pattern to ensure one instance across all tests.
    Allows mocking of Robot Framework's built-in keywords for unit testing.
    """
    _instance = None
    _original_methods = {}
    _mocks = {}

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    @keyword
    def mock_builtin_keyword(self, keyword_name: str, return_value: Any = None, side_effect: Callable = None):
        """Mock a keyword from the BuiltIn library.
        
        Args:
            keyword_name: Name of the BuiltIn keyword to mock
            return_value: Value to return when the keyword is called (optional)
            side_effect: Callable to execute instead (optional)
            
        Returns:
            Mock object for the keyword
            
        Raises:
            AttributeError: If the keyword is not found in BuiltIn library
        """
        lib = BuiltIn()
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

        owner_class = self._original_methods[method_name].__self__.__class__
        setattr(owner_class, method_name, lambda self, *args, **kwargs: mock(*args, **kwargs))

        return mock
