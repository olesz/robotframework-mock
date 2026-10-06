*** Settings ***
Documentation    Test suite for MockResource library functionality

Resource    resources/resource-test.resource
Resource    resources/resource-test-2.resource
Library    MockResource    resource-test.resource    AS    MockResourceTest
Library    MockResource    resource-test-2.resource    AS    MockResourceTest2

Test Teardown    Teardown


*** Test Cases ***
Test Mock Simple Resource
    [Documentation]    Test mocking a simple resource keyword
    MockResourceTest.Mock Keyword    Resource Keyword Test    return_value=test_data

    ${result}=    Resource Keyword Test
    Should Be Equal    ${result}    test_data
    MockResourceTest.Verify Keyword Called    Resource Keyword Test    1

Test Mock With Side Effect
    [Documentation]    Test mocking a resource keyword with side effect
    ${side_effect}=    Evaluate    lambda arg, *args, **kwargs: 'arg1_mod' if 'arg1' in arg else 'arg2_mod'
    MockResourceTest.Mock Keyword    Resource Keyword Test With Argument    side_effect=${side_effect}

    ${result1}=    Resource Keyword Test With Argument    arg1
    ${result2}=    Resource Keyword Test With Argument    arg2
    Should Be Equal    ${result1}    arg1_mod
    Should Be Equal    ${result2}    arg2_mod
    MockResourceTest.Verify Keyword Called    Resource Keyword Test With Argument    2

    MockResourceTest.Reset Mocks

    ${result1}=    Resource Keyword Test With Argument    arg1
    Should Be Equal    ${result1}    arg1

Test Mock Reset
    [Documentation]    Test resetting mocks restores original behavior
    Setup Mocks
    Verify Mocked Behavior
    MockResourceTest.Reset Mocks
    Verify Original Behavior

Test Recorded Call Arguments Are Resolved
    [Documentation]    Arguments reach the mock with variables resolved, not as
    ...    the raw text written at the call site.
    VAR    ${query}=    SELECT 1
    MockResourceTest.Mock Keyword    Resource Keyword Test With Argument    return_value=mocked

    Resource Keyword Test With Argument    ${query} commit;

    ${args}=    MockResourceTest.Get Keyword Call Args    Resource Keyword Test With Argument
    Should Be Equal    ${args}[0]    SELECT 1 commit;

Test Recorded Named Arguments
    [Documentation]    A name=value argument is recorded as a named argument when the
    ...    keyword declares that argument.
    MockResourceTest.Mock Keyword    Resource Keyword Test With Named Arguments    return_value=mocked

    Resource Keyword Test With Named Arguments    value    option=custom

    ${args}=      MockResourceTest.Get Keyword Call Args      Resource Keyword Test With Named Arguments
    ${kwargs}=    MockResourceTest.Get Keyword Call Kwargs    Resource Keyword Test With Named Arguments
    Should Be Equal    ${args}[0]           value
    Should Be Equal    ${kwargs}[option]    custom

Test Undeclared Named Argument Stays Positional
    [Documentation]    A value containing = is not mistaken for a named argument when
    ...    the keyword does not declare that name.
    MockResourceTest.Mock Keyword    Resource Keyword Test With Named Arguments    return_value=mocked

    Resource Keyword Test With Named Arguments    not_an_argument=stays_positional

    ${args}=      MockResourceTest.Get Keyword Call Args      Resource Keyword Test With Named Arguments
    ${kwargs}=    MockResourceTest.Get Keyword Call Kwargs    Resource Keyword Test With Named Arguments
    Should Be Equal    ${args}[0]    not_an_argument=stays_positional
    Should Be Empty    ${kwargs}

Test Verify Keyword Called With
    [Documentation]    Verification succeeds for any matching call and reports the
    ...    recorded calls when none matches.
    MockResourceTest.Mock Keyword    Resource Keyword Test With Argument    return_value=mocked

    Resource Keyword Test With Argument    first
    Resource Keyword Test With Argument    second

    MockResourceTest.Verify Keyword Called With    Resource Keyword Test With Argument    first
    MockResourceTest.Verify Keyword Called With    Resource Keyword Test With Argument    second
    ${count}=    MockResourceTest.Get Keyword Call Count    Resource Keyword Test With Argument
    Should Be Equal As Integers    ${count}    2

    Run Keyword And Expect Error    *was not called with*
    ...    MockResourceTest.Verify Keyword Called With    Resource Keyword Test With Argument    third

Test Call Inspection Of Unmocked Or Missing Call
    [Documentation]    Inspecting a keyword that was not mocked, or a call index that
    ...    does not exist, fails with an explanatory error.
    Run Keyword And Expect Error    Keyword 'Resource Keyword Test' was not mocked
    ...    MockResourceTest.Get Keyword Call Args    Resource Keyword Test

    MockResourceTest.Mock Keyword    Resource Keyword Test    return_value=mocked
    Resource Keyword Test
    Run Keyword And Expect Error    *No call recorded at index 5*
    ...    MockResourceTest.Get Keyword Call Args    Resource Keyword Test    index=5

Test Side Effect Receives Resolved Arguments
    [Documentation]    A side effect is called with the resolved arguments, so it can
    ...    branch on real values instead of raw variable text.
    ${side_effect}=    Evaluate    lambda arg, option='none': f'{arg}|{option}'
    MockResourceTest.Mock Keyword    Resource Keyword Test With Named Arguments    side_effect=${side_effect}
    VAR    ${value}=    resolved

    ${result}=    Resource Keyword Test With Named Arguments    ${value}    option=custom

    Should Be Equal    ${result}    resolved|custom


*** Keywords ***
Setup Mocks
    [Documentation]    Setup mocks for both resource test libraries
    MockResourceTest.Mock Keyword    Resource Keyword Test    return_value=test_data
    MockResourceTest2.Mock Keyword    Resource Keyword Test 2    return_value=test_data_2

Verify Mocked Behavior
    [Documentation]    Verify mocked keywords return expected values
    ${result}=    Resource Keyword Test
    Should Be Equal    ${result}    test_data
    ${result}=    Resource Keyword Test 2
    Should Be Equal    ${result}    test_data_2
    MockResourceTest.Verify Keyword Called    Resource Keyword Test    1
    MockResourceTest2.Verify Keyword Called    Resource Keyword Test 2    1

Verify Original Behavior
    [Documentation]    Verify keywords return original values after reset
    ${result}=    Resource Keyword Test
    Should Be Equal    ${result}    data
    ${result}=    Resource Keyword Test 2
    Should Be Equal    ${result}    test_data_2
    MockResourceTest2.Verify Keyword Called    Resource Keyword Test 2    2

Teardown
    [Documentation]    Reset all mocks after each test
    MockResourceTest.Reset Mocks
