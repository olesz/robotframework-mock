*** Settings ***
Documentation    Test suite for MockLibrary functionality

Library    DateTime
Library    MockLibrary    DateTime    AS    MockDateTime
Library    MockLibrary    BuiltIn    AS    MockBuiltin

Test Teardown    Teardown


*** Test Cases ***
Test Mock Simple Module
    [Documentation]    Test mocking a simple module keyword
    MockDateTime.Mock Keyword    Convert Time    return_value=test_data

    ${result}=    Convert Time    2024-01-01 12:00:00
    Should Be Equal    ${result}    test_data
    MockDateTime.Verify Keyword Called    Convert Time    1

Test Mock Simple Module Multiple Values
    [Documentation]    Test mocking with multiple return values
    ${return_values}=    Evaluate    ['test_data', 'test_data_two']
    MockDateTime.Mock Keyword    Convert Time    return_value=${return_values}

    ${result}    ${result_2}=    Convert Time    2024-01-01 12:00:00
    Should Be Equal    ${result}    test_data
    Should Be Equal    ${result_2}    test_data_two
    MockDateTime.Verify Keyword Called    Convert Time    1

Test Mock Simple Class
    [Documentation]    Test mocking a BuiltIn keyword
    MockBuiltin.Mock Keyword    Convert To Binary    return_value=test_data_2

    ${result}=    Convert To Binary    aaa
    Should Be Equal    ${result}    test_data_2
    MockBuiltin.Verify Keyword Called    Convert To Binary    1

Test Mock With Side Effect
    [Documentation]    Test mocking with side effect function
    ${side_effect}=    Evaluate    lambda time, *args, **kwargs: 'morning' if '08:00' in time else 'evening'
    MockDateTime.Mock Keyword    Convert Time    side_effect=${side_effect}

    ${result1}=    Convert Time    2024-01-01 08:00:00
    ${result2}=    Convert Time    2024-01-01 20:00:00
    Should Be Equal    ${result1}    morning
    Should Be Equal    ${result2}    evening
    MockDateTime.Verify Keyword Called    Convert Time    2

Test Mock Reset
    [Documentation]    Test resetting mocks restores original behavior
    Setup Library Mocks
    Verify Library Mocked Behavior
    MockDateTime.Reset Mocks
    Verify Library Original Behavior


*** Keywords ***
Setup Library Mocks
    [Documentation]    Setup mocks for DateTime and BuiltIn libraries
    MockDateTime.Mock Keyword    Convert Time    return_value=test_data
    MockBuiltin.Mock Keyword    Convert To Binary    return_value=test_data_2

Verify Library Mocked Behavior
    [Documentation]    Verify mocked keywords return expected values
    ${result}=    Convert Time    2024-01-01 12:00:00
    Should Be Equal    ${result}    test_data
    ${result}=    Convert To Binary    aaa
    Should Be Equal    ${result}    test_data_2
    MockDateTime.Verify Keyword Called    Convert Time    1
    MockBuiltin.Verify Keyword Called    Convert To Binary    1

Verify Library Original Behavior
    [Documentation]    Verify keywords return original values after reset
    ${result}=    Convert Time    12:00:00
    Should Be True    ${result} == 43200.0
    ${result}=    Convert To Binary    aaa
    Should Be Equal    ${result}    test_data_2
    MockBuiltin.Verify Keyword Called    Convert To Binary    2

Teardown
    [Documentation]    Reset all mocks after each test
    MockDateTime.Reset Mocks
    MockBuiltin.Reset Mocks
