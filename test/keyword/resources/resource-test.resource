*** Settings ***
Library    Collections


*** Variables ***
@{LIFECYCLE_STEPS}


*** Keywords ***
Resource Keyword Test
    RETURN    data

Resource Keyword Test With Argument
    [Arguments]    ${arg}
    RETURN    ${arg}

Resource Keyword Test With Named Arguments
    [Arguments]    ${arg}    ${option}=default
    RETURN    ${arg}-${option}

Resource Keyword Returning Data
    RETURN    original

Resource Keyword With Setup And Teardown
    [Documentation]    Setup and teardown record that they ran, and the teardown fails unless
    ...    the body has registered itself, mimicking a keyword that releases a lock its body
    ...    acquired.
    [Setup]    Record Lifecycle Step    setup
    Record Lifecycle Step    body
    RETURN    original
    [Teardown]    Release Registered Body

Record Lifecycle Step
    [Documentation]    Append a lifecycle step to the recorded list.
    [Arguments]    ${step}
    Append To List    ${LIFECYCLE_STEPS}    ${step}

Reset Lifecycle Steps
    [Documentation]    Empty the recorded steps in place, so each test starts clean.
    Evaluate    $LIFECYCLE_STEPS.clear()

Pretend Body Ran
    [Documentation]    Register the body step without running the body, so the teardown of a
    ...    mocked keyword can succeed.
    Record Lifecycle Step    body

Release Registered Body
    [Documentation]    Fail unless the body ran, then record the release.
    Should Contain    ${LIFECYCLE_STEPS}    body    The body never registered itself
    Append To List    ${LIFECYCLE_STEPS}    teardown
