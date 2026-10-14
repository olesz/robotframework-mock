*** Settings ***
Documentation    Tests for the call order recorded across all mock instances.
...
...              Each library instance can only order the calls it mocked itself, so these
...              tests exercise the ordering that spans instances - two resources and a
...              library - which is what Get Keyword Call Order cannot report.

Resource    resources/resource-test.resource
Resource    resources/resource-test-2.resource
Library     resources/StaticLibrary.py
Library     MockResource    resource-test.resource    AS    MockFirst
Library     MockResource    resource-test-2.resource    AS    MockSecond
Library     MockLibrary    StaticLibrary    AS    MockStatic
Library     MockCallOrder

Test Setup       Reset Global Call Order
Test Teardown    Teardown


*** Test Cases ***
Test Order Spans Separate Resource Instances
    [Documentation]    Calls mocked through two different MockResource instances appear in
    ...    one order, which neither instance could report on its own.
    MockFirst.Mock Keyword    Resource Keyword Test    return_value=first
    MockSecond.Mock Keyword    Resource Keyword Test 2    return_value=second

    Resource Keyword Test 2
    Resource Keyword Test
    Resource Keyword Test 2

    ${order}=    Get Global Call Order
    VAR    @{expected}=    Resource Keyword Test 2    Resource Keyword Test
    ...    Resource Keyword Test 2
    Should Be Equal    ${order}    ${expected}

Test Order Spans A Resource And A Library
    [Documentation]    The timeline covers MockLibrary and MockResource alike, so a resource
    ...    keyword and a library keyword can be ordered against each other.
    MockFirst.Mock Keyword    Resource Keyword Test    return_value=first
    MockStatic.Mock Keyword    Execute Query    return_value=rows

    Execute Query    SELECT 1
    Resource Keyword Test

    ${order}=    Get Global Call Order
    VAR    @{expected}=    Execute Query    Resource Keyword Test
    Should Be Equal    ${order}    ${expected}

Test Qualified Order Names The Mocked Target
    [Documentation]    Qualifying tells two identically named keywords apart by the resource
    ...    or library they were mocked on.
    MockFirst.Mock Keyword    Resource Keyword Test    return_value=first
    MockStatic.Mock Keyword    Execute Query    return_value=rows

    Resource Keyword Test
    Execute Query    SELECT 1

    ${order}=    Get Global Call Order    qualified=${True}
    VAR    @{expected}=    resource-test.resource.Resource Keyword Test
    ...    StaticLibrary.Execute Query
    Should Be Equal    ${order}    ${expected}

Test Reset Clears The Recorded Order
    [Documentation]    Reset Global Call Order forgets what was recorded, which is what keeps
    ...    one test from seeing another test's calls.
    MockFirst.Mock Keyword    Resource Keyword Test    return_value=first
    Resource Keyword Test
    ${before}=    Get Global Call Order
    Should Not Be Empty    ${before}

    Reset Global Call Order

    ${after}=    Get Global Call Order
    Should Be Empty    ${after}

Test Uncalled Keywords Are Absent From The Order
    [Documentation]    Mocking records nothing by itself - only calls are recorded.
    MockFirst.Mock Keyword    Resource Keyword Test    return_value=first
    ${order}=    Get Global Call Order
    Should Be Empty    ${order}

Test Per Instance Reset Keeps The Global Order
    [Documentation]    Resetting one instance must not discard another instance's history,
    ...    or a two-instance assertion would depend on the order the mocks were reset in.
    MockFirst.Mock Keyword    Resource Keyword Test    return_value=first
    MockSecond.Mock Keyword    Resource Keyword Test 2    return_value=second
    Resource Keyword Test
    Resource Keyword Test 2

    MockFirst.Reset Mocks

    ${order}=    Get Global Call Order
    VAR    @{expected}=    Resource Keyword Test    Resource Keyword Test 2
    Should Be Equal    ${order}    ${expected}

Test Repeated Calls Appear Once Each
    [Documentation]    A keyword called three times appears three times, so a test can assert
    ...    how many times something happened relative to the other calls.
    MockFirst.Mock Keyword    Resource Keyword Test    return_value=first
    MockSecond.Mock Keyword    Resource Keyword Test 2    return_value=second

    Resource Keyword Test
    Resource Keyword Test
    Resource Keyword Test 2

    ${order}=    Get Global Call Order
    VAR    @{expected}=    Resource Keyword Test    Resource Keyword Test
    ...    Resource Keyword Test 2
    Should Be Equal    ${order}    ${expected}

Test Failing Calls Are Recorded
    [Documentation]    A call that raised still happened, so it has to appear in the order -
    ...    otherwise a retry sequence could not be asserted.
    MockFirst.Mock Keyword    Resource Keyword Test    side_effect=${{ RuntimeError('boom') }}
    MockSecond.Mock Keyword    Resource Keyword Test 2    return_value=second

    Run Keyword And Expect Error    *boom*    Resource Keyword Test
    Resource Keyword Test 2

    ${order}=    Get Global Call Order
    VAR    @{expected}=    Resource Keyword Test    Resource Keyword Test 2
    Should Be Equal    ${order}    ${expected}


*** Keywords ***
Teardown
    [Documentation]    Reset every mock and the shared order after each test.
    MockFirst.Reset Mocks
    MockSecond.Reset Mocks
    MockStatic.Reset Mocks
    Reset Global Call Order
