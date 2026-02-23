# robotframework-mock

A Robot Framework library for mocking keywords in unit tests.

## Installation

### From PyPI (once published)

```bash
pip install robotframework-mock
```

### From source

```bash
git clone https://github.com/yourusername/robotframework-mock.git
cd robotframework-mock
pip install .
```

### For development

```bash
pip install -e .
pip install -r requirements-dev.txt
```

## Features

- Mock keywords from any Robot Framework library
- Mock Robot Framework's BuiltIn keywords
- Support for keywords with custom names via @keyword decorator
- Verify keyword calls and call counts
- Simple API with three main keywords

## Usage

### Mock Library Keywords

Import the library you want to mock, then create a MockLibrary instance for it:

```robot
*** Settings ***
Library    DatabaseLibrary
Library    MockLibrary    DatabaseLibrary    WITH NAME    MockDB

*** Test Cases ***
Test With Mocked Keyword
    MockDB.Mock Keyword    query    return_value=test_data
    ${result}=    DatabaseLibrary.Query    SELECT * FROM users
    Should Be Equal    ${result}    test_data
    MockDB.Reset Mocks
```

### Verify Calls

Verify that a keyword was called and optionally check the call count:

```robot
*** Test Cases ***
Test Keyword Was Called
    MockDB.Mock Keyword    execute_sql    return_value=${None}
    Process User Registration
    MockDB.Verify Keyword Called    execute_sql    times=1
    MockDB.Reset Mocks
```

### Mock BuiltIn Keywords

Mock Robot Framework's built-in keywords using the same MockLibrary with "BuiltIn" as the library name:

```robot
*** Settings ***
Library    MockLibrary    BuiltIn    WITH NAME    MockBin

*** Test Cases ***
Test BuiltIn Mock
    MockBin.Mock Keyword    Convert To Binary    return_value=test_data
    ${result}=    Convert To Binary    aaa
    Should Be Equal    ${result}    test_data
    MockBin.Reset Mocks
```

### Mock Multiple Libraries

You can mock multiple libraries in the same test:

```robot
*** Settings ***
Library    DatabaseLibrary
Library    RequestsLibrary
Library    MockLibrary    DatabaseLibrary    WITH NAME    MockDB
Library    MockLibrary    RequestsLibrary    WITH NAME    MockReq

*** Test Cases ***
Test Multiple Mocks
    MockDB.Mock Keyword    query    return_value=user_data
    MockReq.Mock Keyword    get    return_value=api_response
    # Your test code here
    MockDB.Reset Mocks
    MockReq.Reset Mocks
```

## Keywords

### Mock Keyword

Mock a keyword with a return value or side effect.

**Arguments:**
- `keyword_name` - Name of the keyword to mock
- `return_value` - Value to return when called (optional)
- `side_effect` - Callable to execute instead (optional)

**Example:**
```robot
MockDB.Mock Keyword    query    return_value=test_data
```

### Reset Mocks

Restore all mocked keywords to their original implementations.

**Example:**
```robot
MockDB.Reset Mocks
```

### Verify Keyword Called

Verify a keyword was called, optionally checking call count.

**Arguments:**
- `keyword_name` - Name of the keyword to verify
- `times` - Expected number of calls (optional)

**Example:**
```robot
MockDB.Verify Keyword Called    execute_sql    times=1
```

## How It Works

MockLibrary dynamically replaces keyword implementations:
1. Wraps the target library instance
2. Resolves keyword names to function names (handles @keyword decorator)
3. Stores original methods before mocking
4. Replaces methods with mock implementations using Python's unittest.mock.Mock
5. Returns mocked values or executes side effects
6. Tracks call counts for verification
7. Raises AttributeError if attempting to mock a non-existent keyword

## Notes

- The library uses `ROBOT_LIBRARY_SCOPE = 'GLOBAL'` to maintain state across test cases
- Built on Python's unittest.mock.Mock for robust mocking capabilities
- Supports any Robot Framework library, including BuiltIn

## License

See LICENSE file for details.