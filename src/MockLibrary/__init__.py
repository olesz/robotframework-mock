"""Mock library for Robot Framework keyword mocking in unit tests."""
# pylint: disable=invalid-name
import inspect
from typing import Any, Callable
from unittest.mock import Mock
from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn


def _get_library_instance(library_name_or_alias):
    """Retrieve a library instance from Robot Framework's runtime.
    
    Args:
        library_name_or_alias: Name or alias of the library to retrieve
        
    Returns:
        The library instance object
        
    Raises:
        RuntimeError: If the library is not found in Robot Framework
    """
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
        """Initialize MockLibrary with a target library to mock.
        
        Args:
            library_name_or_alias: Name or alias of the library to mock
            lib: Optional library instance (for testing purposes)
        """
        # Store original method references before mocking
        self._original_methods = {}
        # Store Mock objects for verification
        self._mocks = {}
        # Get or set the library instance to mock
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
        
        Args:
            keyword_name: Name of the keyword to mock (case-insensitive)
            return_value: Value to return when the keyword is called
            side_effect: Callable to execute instead of returning a value
        
        Example:
            | MockDB.Mock Keyword | query | return_value=test_data |
        """
        lib = self._library_instance
        # Convert keyword name to method name format (lowercase with underscores)
        method_name = keyword_name.lower().replace(' ', '_')

        # Only store original method once per keyword
        if method_name not in self._original_methods:
            original_method = None
            # Try direct attribute lookup first
            try:
                original_method = getattr(lib, method_name)
            except AttributeError:
                # If not found, search for methods with @keyword decorator custom names
                for name, method in inspect.getmembers(
                    lib, inspect.ismethod
                ):
                    if (hasattr(method, 'robot_name') and
                            method.robot_name.lower() == keyword_name):
                        original_method = getattr(lib, name)
                        method_name = name
                        break
            # Raise error if keyword doesn't exist
            if not original_method:
                raise AttributeError(f"Keyword '{keyword_name}' not found in {lib}")
            self._original_methods[method_name] = original_method

        # Create Mock object with specified behavior
        mock = Mock(return_value=return_value, side_effect=side_effect)
        self._mocks[method_name] = mock

        # Replace the method on the class or instance
        try:
            # Try to set on the class for bound methods
            owner_class = self._original_methods[method_name].__self__.__class__
            setattr(owner_class, method_name, mock)
        except AttributeError:
            # Fall back to setting on the instance
            setattr(lib, method_name, mock)

        return mock

    @keyword
    def reset_mocks(self):
        """Reset all mocks to their original implementations.
        
        Restores all mocked keywords to their original behavior and clears
        all tracking data.
        
        Example:
            | MockDB.Reset Mocks |
        """
        # Restore each mocked method to its original implementation
        for method_name, original_method in self._original_methods.items():
            try:
                # Restore on the class for bound methods
                owner_class = original_method.__self__.__class__
                setattr(owner_class, method_name, original_method)
            except AttributeError:
                # Restore on the instance
                setattr(self._library_instance, method_name, original_method)

        # Clear all tracking dictionaries
        self._mocks.clear()
        self._original_methods.clear()

    @keyword
    def verify_keyword_called(self, keyword_name: str, times: int = None):
        """Verify that a mocked keyword was called.
        
        Args:
            keyword_name: Name of the keyword to verify
            times: Expected number of calls (optional, if None just checks it was called)
        
        Raises:
            AssertionError: If keyword was not mocked or call count doesn't match
        
        Example:
            | MockDB.Verify Keyword Called | execute_sql | times=1 |
        """
        # Convert keyword name to method name format
        method_name = keyword_name.lower().replace(' ', '_')
        # Check if the keyword was mocked
        if method_name not in self._mocks:
            raise AssertionError(f"Keyword '{keyword_name}' was not mocked")

        # Verify call count if specified
        mock = self._mocks[method_name]
        if times is not None and mock.call_count != times:
            raise AssertionError(f"Expected {times} calls, got {mock.call_count}")
