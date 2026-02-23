"""Mock implementations of built-in functions for testing."""
from mock_library import MockLibrary
from robot.libraries.BuiltIn import BuiltIn


class MockBuiltin(MockLibrary):  # pylint: disable=too-few-public-methods
    """Mock Robot Framework's BuiltIn library keywords.
    
    Example:
        | Library | mock.MockBuiltin | WITH NAME | MockBin |
        | MockBin.Mock Builtin Keyword | Convert To Binary | return_value=test_data |
        | ${result}= | Convert To Binary | aaa |
        | Should Be Equal | ${result} | test_data |
    """

    def __init__(self):
        super().__init__("", BuiltIn())
