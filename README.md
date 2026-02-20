# robotframework-mock

A Robot Framework library that enables unit testing of keywords by providing mocking capabilities for other keywords they depend on.

## Installation

```bash
pip install -r requirements.txt
```

## Features

- Mock keywords from any Python library
- Mock built-in Robot Framework keywords
- Verify keyword calls and call counts
- Seamless integration - wrapped libraries expose all original keywords plus mocking capabilities

## Usage

### Basic Mocking

Import your library through `MockableLibrary` to add mocking capabilities:

```robot
*** Settings ***
Library    mock.MockLibrary    MyCustomLibrary
Library    mock.MockLibrary    DatabaseLibrary    WITH NAME    MockDB

*** Test Cases ***
Test Keyword With Mocked Dependencies
    Mock Keyword    database_query    return_value=test_data
    ${result}=    My Keyword Under Test
    Should Be Equal    ${result}    expected_value
    Reset Mocks
```

### Verify Calls

```robot
*** Test Cases ***
Test Keyword Was Called
    Mock Keyword    send_email    return_value=${None}
    Process User Registration
    Verify Keyword Called    send_email    times=1
    Reset Mocks
```

### Mock Built-in Keywords

```robot
*** Test Cases ***
Test With Mocked BuiltIn
    Mock Builtin Keyword    Log    return_value=${None}
    My Keyword That Logs
    Reset Mocks
```

## How It Works

`MockableLibrary` acts as a transparent proxy that:
1. Wraps any Robot Framework library
2. Exposes all original keywords from the wrapped library
3. Adds mocking keywords: `Mock Keyword`, `Reset Mocks`, `Verify Keyword Called`, `Mock Builtin Keyword`
4. Intercepts calls to mocked keywords and returns configured values

## API

### Mock Keyword
Mock a keyword from the wrapped library.

**Arguments:**
- `keyword_name`: Name of the keyword to mock
- `return_value`: Value to return when the keyword is called (optional)
- `side_effect`: Callable to execute instead (optional)

### Reset Mocks
Reset all mocks to their original implementations.

### Verify Keyword Called
Verify that a mocked keyword was called.

**Arguments:**
- `keyword_name`: Name of the keyword to verify
- `times`: Expected number of calls (optional)

### Mock Builtin Keyword
Mock a Robot Framework built-in keyword.

**Arguments:**
- `keyword_name`: Name of the built-in keyword to mock
- `return_value`: Value to return when the keyword is called

## License

See LICENSE file for details.