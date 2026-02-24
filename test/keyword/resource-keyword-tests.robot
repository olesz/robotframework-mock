*** Settings ***
Resource    resources/resource-test.resource
Resource    resources/resource-test-2.resource
Library    MockResource    resource-test.resource    WITH NAME    MockResourceTest
Library    MockResource    resource-test-2.resource    WITH NAME    MockResourceTest2

Test Teardown    Teardown

*** Test Cases ***
Test Mock Simple Resource
    MockResourceTest.Mock Keyword    Resource Keyword Test    return_value=test_data

    ${result}=    Resource Keyword Test
    Should Be Equal    ${result}    test_data
    MockResourceTest.Verify Keyword Called    Resource Keyword Test    1

Test Mock With Side Effect
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
    MockResourceTest.Mock Keyword    Resource Keyword Test    return_value=test_data
    MockResourceTest2.Mock Keyword    Resource Keyword Test 2    return_value=test_data_2

    ${result}=    Resource Keyword Test
    Should Be Equal    ${result}    test_data
    ${result}=    Resource Keyword Test 2
    Should Be Equal    ${result}    test_data_2
    MockResourceTest.Verify Keyword Called    Resource Keyword Test    1
    MockResourceTest2.Verify Keyword Called    Resource Keyword Test 2    1

    MockResourceTest.Reset Mocks

    ${result}=    Resource Keyword Test
    Should Be Equal    ${result}    data
    ${result}=    Resource Keyword Test 2
    Should Be Equal    ${result}    test_data_2
    MockResourceTest2.Verify Keyword Called    Resource Keyword Test 2    2

*** Keywords ***
Teardown
    MockResourceTest.Reset Mocks
