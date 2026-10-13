*** Settings ***
Documentation    Test suite for mocking a keyword that is already mocked.
...
...              The body of a mocked keyword is replaced on its first call, so mocking it again
...              must not save that replacement as the original. These tests pin down that
...              Reset Mocks still restores the real keyword, that the new mock starts with an
...              empty call history, and that skip_setup / skip_teardown apply on every call.

Resource    resources/resource-test.resource
Library    MockResource    resource-test.resource    AS    MockResourceTest

Test Teardown    MockResourceTest.Reset Mocks


*** Test Cases ***
Test Remock Still Restores The Real Keyword
    [Documentation]    The body is replaced on the first mocked call, so mocking again must not
    ...    save that replacement as the original. If it did, Reset Mocks would install the mock
    ...    permanently - resource keywords are shared for the whole run, so every later test
    ...    would fail on the unset mock return variable.
    MockResourceTest.Mock Keyword    Resource Keyword Test    return_value=first
    ${first}=    Resource Keyword Test
    MockResourceTest.Mock Keyword    Resource Keyword Test    return_value=second
    ${second}=    Resource Keyword Test
    MockResourceTest.Reset Mocks

    ${restored}=    Resource Keyword Test

    Should Be Equal    ${first}       first
    Should Be Equal    ${second}      second
    Should Be Equal    ${restored}    data

Test Remock Starts A Fresh Call History
    [Documentation]    Replacing the mock replaces what recorded the calls, so the counts and
    ...    arguments a test inspects belong to the current mock only.
    MockResourceTest.Mock Keyword    Resource Keyword Test    return_value=first
    Resource Keyword Test
    MockResourceTest.Mock Keyword    Resource Keyword Test    return_value=second

    MockResourceTest.Verify Keyword Called    Resource Keyword Test    times=0

    Resource Keyword Test
    MockResourceTest.Verify Keyword Called    Resource Keyword Test    times=1

Test Remock Under Another Spelling Restores The Real Keyword
    [Documentation]    Two spellings of one name are one keyword to Robot, so they must share a
    ...    single saved original rather than each saving its own.
    MockResourceTest.Mock Keyword    Resource Keyword Test     return_value=first
    Resource Keyword Test
    MockResourceTest.Mock Keyword    resource_keyword_test    return_value=second
    Resource Keyword Test
    MockResourceTest.Reset Mocks

    ${restored}=    Resource Keyword Test

    Should Be Equal    ${restored}    data

Test Remock Keeping Skip Teardown Still Restores It
    [Documentation]    A teardown suppressed by two consecutive mocks has to come back on reset,
    ...    otherwise the second mock would lose it for the rest of the run.
    Reset Lifecycle Steps
    MockResourceTest.Mock Keyword    Resource Keyword With Setup And Teardown
    ...    return_value=mocked    skip_teardown=${True}
    Resource Keyword With Setup And Teardown
    MockResourceTest.Mock Keyword    Resource Keyword With Setup And Teardown
    ...    return_value=mocked_again    skip_teardown=${True}
    Resource Keyword With Setup And Teardown
    MockResourceTest.Reset Mocks

    ${result}=    Resource Keyword With Setup And Teardown

    Should Be Equal    ${result}    original
    Should Contain     ${LIFECYCLE_STEPS}    teardown

Test Remock Without Skip Teardown Puts The Teardown Back
    [Documentation]    The flag says whether the teardown runs, so dropping it on a re-mock has
    ...    to take effect immediately rather than waiting for a reset.
    Reset Lifecycle Steps
    MockResourceTest.Mock Keyword    Resource Keyword With Setup And Teardown
    ...    return_value=mocked    skip_teardown=${True}
    Resource Keyword With Setup And Teardown
    Should Not Contain    ${LIFECYCLE_STEPS}    teardown

    MockResourceTest.Mock Keyword    Resource Keyword With Setup And Teardown
    ...    return_value=mocked_again

    Run Keyword And Expect Error    *The body never registered itself*
    ...    Resource Keyword With Setup And Teardown
