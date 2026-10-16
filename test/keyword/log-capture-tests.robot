*** Settings ***
Documentation       Tests for the log messages captured while a keyword runs.
...
...                 The point of these tests is the part a unit test cannot reach: Robot
...                 filters messages below the active log level *before* a listener is offered
...                 them, so what a test can see depends on a level the library changes on its
...                 behalf. `Debug Is Captured Because The Level Is Raised` and
...                 `No Level Change Leaves Debug Filtered Out` are the pair that proves it.

Library             Collections
Library             LogCapture

Test Teardown       Stop Capturing Log Messages


*** Test Cases ***
Test Messages Are Captured In Order
    [Documentation]    Every message a keyword logs is recorded, oldest first.
    Start Capturing Log Messages

    Log    first message
    Log    second message

    ${messages}=    Get Captured Log Messages    pattern=*message
    Should Be Equal    ${messages}[0][message]    first message
    Should Be Equal    ${messages}[1][message]    second message

Test The Level Each Message Was Logged At Is Recorded
    [Documentation]    The level is the reason this library exists: a keyword that drops its
    ...    level argument still logs the message, only at the wrong one.
    Start Capturing Log Messages

    Log    a warning    level=WARN

    ${messages}=    Get Captured Log Messages    pattern=a warning
    Should Be Equal    ${messages}[0][level]    WARN

Test Debug Is Captured Because The Level Is Raised
    [Documentation]    At the default INFO level Robot never offers a DEBUG message to a
    ...    listener, so capturing raises the level to DEBUG itself.
    Start Capturing Log Messages

    Log    a debug line    level=DEBUG

    Captured Log Should Contain    a debug line    level=DEBUG

Test No Level Change Leaves Debug Filtered Out
    [Documentation]    The counterpart: with NONE the suite's own level stands, and at INFO the
    ...    DEBUG message is filtered out before the library sees it. Without the raising above,
    ...    this is what every DEBUG assertion would silently do.
    Start Capturing Log Messages    level=NONE

    Log    a debug line    level=DEBUG
    Log    an info line    level=INFO

    ${messages}=    Get Captured Log Messages    pattern=a debug line
    Should Be Empty    ${messages}
    Captured Log Should Contain    an info line    level=INFO

Test The Log Level Is Put Back Afterwards
    [Documentation]    A raised level must not outlive the capture, or the rest of the suite
    ...    would log at DEBUG and the report would fill with noise.
    Set Log Level    INFO
    Start Capturing Log Messages
    ${while_capturing}=    Set Log Level    DEBUG
    Stop Capturing Log Messages

    ${after}=    Set Log Level    INFO
    Should Be Equal    ${while_capturing}    DEBUG
    Should Be Equal    ${after}    INFO

Test Capturing Can Be Limited To A Level
    [Documentation]    Capturing at WARN records the warnings and leaves the INFO chatter out,
    ...    for a test that only cares about what went wrong.
    Start Capturing Log Messages    level=WARN

    Log    chatter    level=INFO
    Log    a real problem    level=WARN

    ${messages}=    Get Captured Log Messages
    Length Should Be    ${messages}    1
    Should Be Equal    ${messages}[0][message]    a real problem

Test Messages Can Be Filtered By Level
    [Documentation]    One capture, read twice: the filters are on reading, not on recording.
    Start Capturing Log Messages

    Log    an info line    level=INFO
    Log    a warning    level=WARN

    ${warnings}=    Get Captured Log Messages    level=WARN
    Length Should Be    ${warnings}    1
    Should Be Equal    ${warnings}[0][message]    a warning

Test Messages Can Be Filtered By Pattern
    [Documentation]    The pattern is a glob, so a partial match needs its own wildcards.
    Start Capturing Log Messages

    Log    rotating the credentials now
    Log    unrelated

    ${matches}=    Get Captured Log Messages    pattern=*credentials*
    Length Should Be    ${matches}    1

Test Starting Again Forgets The Earlier Messages
    [Documentation]    A second capture in the same test starts from nothing, so one phase of a
    ...    test cannot see the previous phase's log.
    Start Capturing Log Messages
    Log    from the first capture

    Start Capturing Log Messages
    Log    from the second capture

    ${messages}=    Get Captured Log Messages    pattern=from the*
    Length Should Be    ${messages}    1
    Should Be Equal    ${messages}[0][message]    from the second capture

Test Stop Returns What Was Captured
    [Documentation]    The convenient form for a test that reads the log once at the end.
    Start Capturing Log Messages
    Log    the only message

    ${messages}=    Stop Capturing Log Messages

    ${texts}=    Evaluate    [m['message'] for m in $messages]
    Should Contain    ${texts}    the only message

Test Nothing Is Captured After Stopping
    [Documentation]    Stopping is what lets a test log its own diagnostics afterwards without
    ...    them appearing in the recording.
    Start Capturing Log Messages
    Log    while capturing
    Stop Capturing Log Messages

    Log    after capturing

    ${messages}=    Get Captured Log Messages    pattern=*capturing
    Length Should Be    ${messages}    1
    Should Be Equal    ${messages}[0][message]    while capturing

Test Nothing Is Captured From An Earlier Test
    [Documentation]    Capturing ends with the test that started it, so this test - which never
    ...    starts one - sees nothing, even though the previous tests captured plenty.
    Log    this test logs without capturing

    ${messages}=    Get Captured Log Messages
    Should Be Empty    ${messages}

Test The Assertion Names The Level It Wanted
    [Documentation]    "Missing" and "logged at another level" are different faults and the
    ...    failure has to tell them apart.
    Start Capturing Log Messages

    Log    a warning    level=WARN

    Run Keyword And Expect Error    *at level INFO*
    ...    Captured Log Should Contain    a warning    level=INFO

Test The Assertion Lists What Was Captured
    [Documentation]    Without the recording in the message, a failing assertion gives the
    ...    reader nothing to go on.
    Start Capturing Log Messages

    Log    what was actually logged

    Run Keyword And Expect Error    *INFO 'what was actually logged'*
    ...    Captured Log Should Contain    something else    level=WARN
    [Teardown]    Stop Capturing Log Messages

Test The Assertion Says So When Nothing Was Captured
    [Documentation]    Forgetting to start capturing is the obvious mistake, so the failure
    ...    names it rather than reporting an absent message.
    Run Keyword And Expect Error    *was capturing started*
    ...    Captured Log Should Contain    anything

Test The Assertion Can Require A Number Of Matches
    [Documentation]    A retry logs the same line once per attempt, so the count is the
    ...    interesting part.
    Start Capturing Log Messages

    Log    retrying
    Log    retrying

    Captured Log Should Contain    retrying    count=2
    Run Keyword And Expect Error    *2 captured messages match, expected 3*
    ...    Captured Log Should Contain    retrying    count=3
