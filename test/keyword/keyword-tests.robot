*** Settings ***
Library    DateTime
Library    src.mock.mock_library.MockLibrary    DateTime    WITH NAME    MockDateTime
Library    src.mock.mock_library.MockLibrary    BuiltIn    WITH NAME    MockBuiltin

Test Teardown    Teardown

*** Test Cases ***
Test Mock Simple Module
    MockDateTime.Mock Keyword    Convert Time    return_value=test_data

    ${result}=    Convert Time    2024-01-01 12:00:00
    Should Be Equal    ${result}    test_data

Test Mock Simple Class
    MockBuiltin.Mock Keyword    Convert To Binary    return_value=test_data_2

    ${result}=    Convert To Binary    aaa
    Should Be Equal    ${result}    test_data_2

Test Mock With Side Effect
    ${side_effect}=    Evaluate    lambda time, *args, **kwargs: 'morning' if '08:00' in time else 'evening'
    MockDateTime.Mock Keyword    Convert Time    side_effect=${side_effect}

    ${result1}=    Convert Time    2024-01-01 08:00:00
    ${result2}=    Convert Time    2024-01-01 20:00:00
    Should Be Equal    ${result1}    morning
    Should Be Equal    ${result2}    evening

Test Mock Reset
    MockDateTime.Mock Keyword    Convert Time    return_value=test_data
    MockBuiltin.Mock Keyword    Convert To Binary    return_value=test_data_2

    ${result}=    Convert Time    2024-01-01 12:00:00
    Should Be Equal    ${result}    test_data
    ${result}=    Convert To Binary    aaa
    Should Be Equal    ${result}    test_data_2

    MockDateTime.Reset Mocks

    ${result}=    Convert Time    12:00:00
    Should Be True    ${result} == 43200.0
    ${result}=    Convert To Binary    aaa
    Should Be Equal    ${result}    test_data_2

*** Keywords ***
Teardown
    MockDateTime.Reset Mocks
    MockBuiltin.Reset Mocks
