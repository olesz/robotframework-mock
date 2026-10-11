*** Settings ***
Documentation    Test suite for how MockResource behaves around branch execution.
...
...              Robot runs the body of every IF/ELSE branch and marks the ones not taken as
...              NOT RUN, so these tests pin down that a mocked keyword in a skipped branch is
...              not recorded as called.

Resource    resources/resource-test.resource
Library    MockResource    resource-test.resource    AS    MockResourceTest

Test Teardown    MockResourceTest.Reset Mocks


*** Test Cases ***
Test A Not Taken Branch Does Not Record A Call
    [Documentation]    Robot runs the body of every IF/ELSE branch and marks the ones not taken
    ...    as NOT RUN, so a mocked keyword in a skipped branch must not be recorded as called.
    ...    Otherwise a test asserting that the other backend was left alone would see a call
    ...    that never happened.
    MockResourceTest.Mock Keyword    Resource Keyword Test              return_value=taken
    MockResourceTest.Mock Keyword    Resource Keyword Returning Data    return_value=skipped

    IF    ${True}
        Resource Keyword Test
    ELSE
        Resource Keyword Returning Data
    END

    ${taken}=      MockResourceTest.Get Keyword Call Count    Resource Keyword Test
    ${skipped}=    MockResourceTest.Get Keyword Call Count    Resource Keyword Returning Data
    Should Be Equal As Integers    ${taken}      1
    Should Be Equal As Integers    ${skipped}    0

Test A Not Taken Branch Does Not Appear In The Call Order
    [Documentation]    The skipped branch is absent from the recorded order too, so an ordering
    ...    assertion is not polluted by a keyword that never ran.
    MockResourceTest.Mock Keyword    Resource Keyword Test              return_value=taken
    MockResourceTest.Mock Keyword    Resource Keyword Returning Data    return_value=skipped

    IF    ${False}
        Resource Keyword Returning Data
    ELSE
        Resource Keyword Test
    END

    ${order}=    MockResourceTest.Get Keyword Call Order
    Should Be Equal    ${order}    ${{ ['Resource Keyword Test'] }}
