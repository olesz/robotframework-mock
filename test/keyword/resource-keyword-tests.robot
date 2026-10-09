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

Test Return Value Can Be Any Object
    [Documentation]    A mocked keyword can return a list or a dictionary, not only a string,
    ...    so keywords that forward a query result or a parsed response can be mocked.
    ${rows}=    Evaluate    [['first', 'second'], ['third']]
    MockResourceTest.Mock Keyword    Resource Keyword Returning Data    return_value=${rows}

    ${result}=    Resource Keyword Returning Data

    Should Be Equal    ${result}[0][0]    first
    Should Be Equal    ${result}[0][1]    second
    Should Be Equal    ${result}[1][0]    third

Test Return Value Object When Called From Another Keyword
    [Documentation]    The object survives an extra keyword scope between the test and the
    ...    mocked keyword, which is how production resources call each other.
    ${payload}=    Evaluate    {'key': 'value'}
    MockResourceTest.Mock Keyword    Resource Keyword Returning Data    return_value=${payload}

    ${result}=    Call Resource Keyword Through Wrapper

    Should Be Equal    ${result}[key]    value

Test Return Value Scalars Are Unchanged
    [Documentation]    Strings and None keep working alongside object return values.
    MockResourceTest.Mock Keyword    Resource Keyword Returning Data    return_value=plain
    ${text}=    Resource Keyword Returning Data
    Should Be Equal    ${text}    plain

    MockResourceTest.Reset Mocks
    MockResourceTest.Mock Keyword    Resource Keyword Returning Data    return_value=${None}
    ${empty}=    Resource Keyword Returning Data
    Should Be Equal    ${empty}    ${None}

Test Setup And Teardown Run By Default
    [Documentation]    Only the body is replaced, so the keyword's own setup and teardown still
    ...    run and stay observable to the test.
    Reset Lifecycle Steps
    Pretend Body Ran
    MockResourceTest.Mock Keyword    Resource Keyword With Setup And Teardown    return_value=mocked

    ${result}=    Resource Keyword With Setup And Teardown

    Should Be Equal    ${result}    mocked
    Should Contain     ${LIFECYCLE_STEPS}    setup
    Should Contain     ${LIFECYCLE_STEPS}    teardown

Test Teardown Fails Without Skip
    [Documentation]    Without skipping, a teardown that depends on what the replaced body did
    ...    fails the mocked call. This is the failure skip_teardown exists to avoid.
    Reset Lifecycle Steps
    MockResourceTest.Mock Keyword    Resource Keyword With Setup And Teardown    return_value=mocked

    Run Keyword And Expect Error    *The body never registered itself*
    ...    Resource Keyword With Setup And Teardown

Test Teardown Can Be Skipped
    [Documentation]    A teardown that cleans up state the replaced body would have created
    ...    can be suppressed, instead of failing the mocked call.
    Reset Lifecycle Steps
    MockResourceTest.Mock Keyword    Resource Keyword With Setup And Teardown
    ...    return_value=mocked    skip_teardown=${True}

    ${result}=    Resource Keyword With Setup And Teardown

    Should Be Equal        ${result}             mocked
    Should Not Contain     ${LIFECYCLE_STEPS}    teardown
    Should Contain         ${LIFECYCLE_STEPS}    setup

Test Setup Can Be Skipped
    [Documentation]    The keyword's setup can be suppressed independently of its teardown.
    Reset Lifecycle Steps
    Pretend Body Ran
    MockResourceTest.Mock Keyword    Resource Keyword With Setup And Teardown
    ...    return_value=mocked    skip_setup=${True}

    Resource Keyword With Setup And Teardown

    Should Not Contain    ${LIFECYCLE_STEPS}    setup
    Should Contain        ${LIFECYCLE_STEPS}    teardown

Test Reset Restores Setup And Teardown
    [Documentation]    After resetting, a suppressed setup and teardown run again.
    Reset Lifecycle Steps
    MockResourceTest.Mock Keyword    Resource Keyword With Setup And Teardown
    ...    return_value=mocked    skip_setup=${True}    skip_teardown=${True}
    Resource Keyword With Setup And Teardown
    MockResourceTest.Reset Mocks

    ${result}=    Resource Keyword With Setup And Teardown

    Should Be Equal    ${result}    original
    Should Contain     ${LIFECYCLE_STEPS}    setup
    Should Contain     ${LIFECYCLE_STEPS}    teardown

Test Mock Applies Regardless Of Case And Spacing
    [Documentation]    Robot matches keyword names case-, space- and underscore-insensitively,
    ...    so a mock registered one way must apply when the call site writes it another way.
    ...    Otherwise the real keyword runs and the mock is silently ignored.
    MockResourceTest.Mock Keyword    Resource Keyword Test    return_value=mocked

    # robocop: off=NAME04,NAME18 - non-canonical spelling is the point of this test
    ${result}=    resource_keyword_test

    Should Be Equal    ${result}    mocked

Test Mock Registered With Different Case Still Applies
    [Documentation]    The same holds in the other direction, when the mock is registered with
    ...    different case than the keyword definition uses.
    MockResourceTest.Mock Keyword    RESOURCE KEYWORD TEST    return_value=mocked

    ${result}=    Resource Keyword Test

    Should Be Equal    ${result}    mocked

Test Call Inspection Matches Regardless Of Case
    [Documentation]    Inspecting recorded calls uses the same name matching, so the lookup
    ...    cannot miss a mock that demonstrably applied.
    MockResourceTest.Mock Keyword    Resource Keyword Test    return_value=mocked
    Resource Keyword Test

    ${count}=    MockResourceTest.Get Keyword Call Count    resource keyword test

    Should Be Equal As Integers    ${count}    1

Test Side Effect That Raises Fails The Keyword Catchably
    [Documentation]    A side effect that raises makes the mocked keyword fail the way a real
    ...    keyword does, so Run Keyword And Ignore Error can catch it. This is what lets a test
    ...    drive the error branch of a keyword that guards its dependency.
    MockResourceTest.Mock Keyword    Resource Keyword Test
    ...    side_effect=${{ RuntimeError('service unavailable') }}

    ${status}    ${message}=    Run Keyword And Ignore Error    Resource Keyword Test

    Should Be Equal    ${status}     FAIL
    Should Be Equal    ${message}    service unavailable

Test Side Effect That Raises Can Be Caught By Try Except
    [Documentation]    The failure is a normal Robot failure, so TRY/EXCEPT matches it on its
    ...    message like any other.
    MockResourceTest.Mock Keyword    Resource Keyword Test    side_effect=${{ ValueError('bad input') }}

    TRY
        Resource Keyword Test
        Fail    The mocked keyword should have failed.
    EXCEPT    bad input
        Log    The raising side effect was caught.
    END

Test Side Effect That Raises Still Records The Call
    [Documentation]    A failing call is still a call, so it remains visible to the call
    ...    inspection keywords.
    MockResourceTest.Mock Keyword    Resource Keyword Test    side_effect=${{ RuntimeError('nope') }}

    Run Keyword And Ignore Error    Resource Keyword Test    first-argument

    MockResourceTest.Verify Keyword Called    Resource Keyword Test    times=1
    ${args}=    MockResourceTest.Get Keyword Call Args    Resource Keyword Test
    Should Be Equal    ${args}[0]    first-argument

Test Call Order Across Mocked Keywords
    [Documentation]    The order in which different mocked keywords were called is reported, so
    ...    a sequence such as "connect before querying" can be asserted. An individual mock's
    ...    call history cannot show this, since it knows nothing about its siblings.
    MockResourceTest.Mock Keyword    Resource Keyword Test                 return_value=first
    MockResourceTest.Mock Keyword    Resource Keyword Returning Data       return_value=second

    Resource Keyword Returning Data
    Resource Keyword Test

    ${order}=    MockResourceTest.Get Keyword Call Order
    Should Be Equal    ${order}
    ...    ${{ ['Resource Keyword Returning Data', 'Resource Keyword Test'] }}

Test Call Order Records Repeated Calls
    [Documentation]    A keyword called more than once appears once per call, so a repeated
    ...    step is visible rather than collapsed.
    MockResourceTest.Mock Keyword    Resource Keyword Test             return_value=a
    MockResourceTest.Mock Keyword    Resource Keyword Returning Data   return_value=b

    Resource Keyword Test
    Resource Keyword Returning Data
    Resource Keyword Test

    ${order}=    MockResourceTest.Get Keyword Call Order
    Should Be Equal    ${order}
    ...    ${{ ['Resource Keyword Test', 'Resource Keyword Returning Data', 'Resource Keyword Test'] }}

Test Call Order Omits Keywords That Were Never Called
    [Documentation]    Mocking a keyword does not put it in the order; only calls do.
    MockResourceTest.Mock Keyword    Resource Keyword Test             return_value=a
    MockResourceTest.Mock Keyword    Resource Keyword Returning Data   return_value=b

    Resource Keyword Test

    ${order}=    MockResourceTest.Get Keyword Call Order
    Should Be Equal    ${order}    ${{ ['Resource Keyword Test'] }}

Test Call Order Is Empty Before Any Call
    [Documentation]    With nothing called the order is empty rather than undefined.
    MockResourceTest.Mock Keyword    Resource Keyword Test    return_value=a

    ${order}=    MockResourceTest.Get Keyword Call Order

    Should Be Empty    ${order}

Test Call Order Is Forgotten On Reset
    [Documentation]    Resetting clears the recorded order, so one test cannot see the calls of
    ...    a previous one.
    MockResourceTest.Mock Keyword    Resource Keyword Test    return_value=a
    Resource Keyword Test
    MockResourceTest.Reset Mocks

    ${order}=    MockResourceTest.Get Keyword Call Order

    Should Be Empty    ${order}

Test Call Order Ignores Calls On A Returned Object
    [Documentation]    Calling a method on a mocked keyword's return value is not a keyword
    ...    call, so it must not appear in the order.
    ${response}=    Evaluate    types.SimpleNamespace(json=lambda: {'ok': True})    modules=types
    MockResourceTest.Mock Keyword    Resource Keyword Returning Data    return_value=${response}

    ${result}=    Resource Keyword Returning Data
    Call Method    ${result}    json

    ${order}=    MockResourceTest.Get Keyword Call Order
    Should Be Equal    ${order}    ${{ ['Resource Keyword Returning Data'] }}

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

Call Resource Keyword Through Wrapper
    [Documentation]    Put a keyword scope between the test and the mocked keyword.
    ${inner}=    Resource Keyword Returning Data
    RETURN    ${inner}
