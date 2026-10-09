*** Settings ***
Documentation    Test suite for MockLibrary functionality

Library    DateTime
Library    MockLibrary    DateTime    AS    MockDateTime
Library    MockLibrary    BuiltIn    AS    MockBuiltin
Library    resources/DynamicLibrary.py
Library    MockLibrary    DynamicLibrary    ${CURDIR}/resources/dynamic_library_resolver.py    AS    MockDynamic
Library    resources/StaticLibrary.py
Library    MockLibrary    StaticLibrary    AS    MockStatic

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

Test Call Inspection
    [Documentation]    Recorded positional and named arguments of a library keyword
    ...    can be inspected. StaticLibrary declares no argument types, so the
    ...    recorded values are the strings written here on every Robot version.
    MockStatic.Mock Keyword    Execute Query    return_value=mocked

    Execute Query    SELECT 1    timeout=30
    Execute Query    SELECT 2

    ${count}=     MockStatic.Get Keyword Call Count     Execute Query
    ${args}=      MockStatic.Get Keyword Call Args      Execute Query    index=0
    ${kwargs}=    MockStatic.Get Keyword Call Kwargs    Execute Query    index=0
    Should Be Equal As Integers    ${count}              2
    Should Be Equal                ${args}[0]            SELECT 1
    Should Be Equal                ${kwargs}[timeout]    30

Test Verify Library Keyword Called With
    [Documentation]    Verification succeeds for any matching call and fails when no
    ...    recorded call matches.
    MockStatic.Mock Keyword    Execute Query    return_value=mocked

    Execute Query    SELECT 1    timeout=30
    Execute Query    SELECT 2

    MockStatic.Verify Keyword Called With    Execute Query    SELECT 1    timeout=30
    MockStatic.Verify Keyword Called With    Execute Query    SELECT 2
    Run Keyword And Expect Error    *was not called with*
    ...    MockStatic.Verify Keyword Called With    Execute Query    SELECT 3

Test Call Inspection Of Last Call
    [Documentation]    A negative index addresses calls from the end of the list.
    MockBuiltin.Mock Keyword    Convert To Binary    return_value=mocked

    Convert To Binary    first
    Convert To Binary    last

    ${args}=    MockBuiltin.Get Keyword Call Args    Convert To Binary    index=-1
    Should Be Equal    ${args}[0]    last

Test Mock Keyword With A Custom Decorator Name
    [Documentation]    A keyword whose @keyword decorator gives it a name unrelated to its
    ...    method name is mocked by that keyword name, which is the only name a test author
    ...    sees. Matching on the method name alone would not find it.
    MockStatic.Mock Keyword    Is The Target Reachable    return_value=mocked-answer

    ${result}=    Is The Target Reachable    some-host

    Should Be Equal    ${result}    mocked-answer

Test Mock Keyword With A Custom Decorator Name Ignores Case And Spacing
    [Documentation]    The decorator's name is matched the way Robot matches keyword names, so
    ...    the test may write it in any case or with underscores.
    MockStatic.Mock Keyword    is_the_target_reachable    return_value=mocked-answer

    ${result}=    Is The Target Reachable    some-host

    Should Be Equal    ${result}    mocked-answer

Test Call Inspection Works For A Custom Decorator Name
    [Documentation]    A keyword mocked by its decorator name is still inspectable by that
    ...    name, so the test never has to know the underlying method name.
    MockStatic.Mock Keyword    Is The Target Reachable    return_value=mocked-answer

    Is The Target Reachable    some-host

    ${args}=    MockStatic.Get Keyword Call Args    Is The Target Reachable
    Should Be Equal    ${args}[0]    some-host
    MockStatic.Verify Keyword Called    Is The Target Reachable    times=1

Test Library Call Order Across Mocked Keywords
    [Documentation]    Ordering works for library keywords as well, so a sequence spanning two
    ...    keywords of the same library can be asserted.
    MockStatic.Mock Keyword     Execute Query        return_value=rows
    MockBuiltin.Mock Keyword    Convert To Binary    return_value=mocked

    Execute Query    SELECT 1
    Convert To Binary    aaa
    Execute Query    SELECT 2

    ${static_order}=    MockStatic.Get Keyword Call Order
    ${builtin_order}=   MockBuiltin.Get Keyword Call Order
    Should Be Equal    ${static_order}     ${{ ['Execute Query', 'Execute Query'] }}
    Should Be Equal    ${builtin_order}    ${{ ['Convert To Binary'] }}

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

Test Mock Dynamic Library With Custom Resolver
    [Documentation]    Test mocking a dynamic library keyword using a custom resolver
    MockDynamic.Mock Keyword    dynamic_greeting    return_value=mocked_greeting
    ${result}=    Dynamic Greeting    world
    Should Be Equal    ${result}    mocked_greeting
    MockDynamic.Verify Keyword Called    dynamic_greeting    1


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
    MockDynamic.Reset Mocks
    MockStatic.Reset Mocks
