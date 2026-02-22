from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn
from typing import Any, Callable
from src.mock.lib.MockLibraryWorker import MockLibraryWorker

class MockLibrary(object):
    """A Robot Framework library that enables unit testing of keywords by providing mocking capabilities.
    
    MockLibrary wraps another Robot Framework library and allows you to mock its keywords.
    Uses a singleton pattern - one mock instance per library name/alias.
    
    Example:
        | Library | DatabaseLibrary |
        | Library | mock.MockLibrary | DatabaseLibrary | WITH NAME | MockDB |
        | Suite Setup | MockDB.Activate Mock |
    """
    _instances = {}
    _initialized = []
    _mocks = {}
    _original_methods = {}
    _local_keywords = ['mock_keyword', 'reset_mocks', 'verify_keyword_called', 'activate_mock']

    def __new__(cls, library_name_or_alias: str):
        if library_name_or_alias not in cls._instances:
            cls._instances[library_name_or_alias] = super().__new__(cls)
        return cls._instances[library_name_or_alias]

    def __init__(self, library_name_or_alias: str):
        if library_name_or_alias in self._initialized:
            return
        self._library_name_or_alias = library_name_or_alias
        self._mock_library_instance = MockLibraryWorker(self._get_library_instance())
        self._monkey_patch_library()
        self._initialized.append(library_name_or_alias)

    def _get_library_instance(self):
        lib = BuiltIn()._namespace._kw_store.libraries[self._library_name_or_alias].instance
        if not lib:
            raise RuntimeError(f"Library with name {self._library_name_or_alias} is not found in robot. Import it first!")
        return lib

    def _monkey_patch_library(self):
        BuiltIn()._namespace._kw_store.libraries[self._library_name_or_alias].instance = self._mock_library_instance

    @keyword
    def mock_keyword(self, keyword_name: str, return_value: Any = None, side_effect: Callable = None):
        """Mock a keyword from the wrapped library.
        
        Args:
            keyword_name: Name of the keyword to mock (supports both function names and @keyword decorator names)
            return_value: Value to return when the keyword is called (optional)
            side_effect: Callable to execute instead (optional)
            
        Example:
            | MockDB.Mock Keyword | query | return_value=test_data |
            | ${result}= | DatabaseLibrary.Query | SELECT * FROM users |
        """
        self._mock_library_instance.mock_keyword(keyword_name, return_value, side_effect)

    @keyword
    def reset_mocks(self):
        """Reset all mocks to their original implementations.
        
        Example:
            | MockDB.Reset Mocks |
        """
        self._mock_library_instance.reset_mocks()

    @keyword
    def verify_keyword_called(self, keyword_name: str, times: int = None):
        """Verify that a mocked keyword was called.
        
        Args:
            keyword_name: Name of the keyword to verify
            times: Expected number of calls (optional, if omitted just verifies it was called)
            
        Example:
            | MockDB.Verify Keyword Called | execute_sql | times=1 |
        """
        self._mock_library_instance.verify_keyword_called(keyword_name, times)
