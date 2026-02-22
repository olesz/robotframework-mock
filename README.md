# robotframework-mock

A Robot Framework library that enables unit testing of keywords by providing mocking capabilities for other keywords they depend on.

## Installation

```bash
pip install -r requirements.txt
```

## Features

- Mock keywords from any Robot Framework library
- Support for keywords with custom names via @keyword decorator
- Verify keyword calls and call counts
- Singleton pattern - one mock instance per library
- Explicit mock activation for controlled testing

## Usage

### Basic Mocking

Import your library through `MockLibrary` and activate mocking:

```robot
*** Settings ***
Library    DatabaseLibrary
Library    RequestsLibrary
Library    mock.MockLibrary    DatabaseLibrary    WITH NAME    MockDB
Library    mock.MockLibrary    RequestsLibrary    WITH NAME    MockReq

Suite Setup    Run Keywords    MockDB.Activate Mock    AND    MockReq.Activate Mock

*** Test Cases ***
Test Keyword With Mocked Dependencies
    MockDB.Mock Keyword    query    return_value=test_data
    ${result}=    DatabaseLibrary.Query    SELECT * FROM users
    Should Be Equal    ${result}    test_data
    MockDB.Reset Mocks
```

### Verify Calls

```robot
*** Test Cases ***
Test Keyword Was Called
    MockDB.Mock Keyword    execute_sql    return_value=${None}
    Process User Registration
    MockDB.Verify Keyword Called    execute_sql    times=1
    MockDB.Reset Mocks
```

### Mock Keywords with Custom Names

Supports keywords decorated with @keyword("Custom Name"):

```robot
*** Test Cases ***
Test HTTP Method Keywords
    MockReq.Mock Keyword    POST    return_value=test_response
    ${result}=    RequestsLibrary.POST    url    data
    Should Be Equal    ${result}    test_response
```

## How It Works

`MockLibrary` uses a worker pattern:
1. Creates a singleton instance per library name/alias
2. Wraps the target library with MockLibraryWorker
3. On `Activate Mock`, replaces the library instance in Robot's namespace
4. Intercepts keyword calls via __getattr__ proxy
5. Resolves keyword names to function names (handles @keyword decorator)
6. Returns mocked values or delegates to original implementation

## API

### Activate Mock
Activates mocking by replacing the library instance in Robot's namespace.

**Must be called before mocking keywords (typically in Suite Setup).**

### Mock Keyword
Mock a keyword from the wrapped library.

**Arguments:**
- `keyword_name`: Name of the keyword to mock (supports both function names and @keyword decorator names)
- `return_value`: Value to return when the keyword is called (optional)
- `side_effect`: Callable to execute instead (optional)

### Reset Mocks
Reset all mocks to their original implementations.

### Verify Keyword Called
Verify that a mocked keyword was called.

**Arguments:**
- `keyword_name`: Name of the keyword to verify
- `times`: Expected number of calls (optional, if omitted just verifies it was called)

## License

See LICENSE file for details.