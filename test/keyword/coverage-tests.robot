*** Settings ***
Documentation    Test suite demonstrating MockCoverage resource keyword coverage.
...              Exercises 3 of the 4 keywords in coverage-demo.resource,
...              yielding 75% coverage.

Resource    resources/coverage-demo.resource


*** Test Cases ***
Test Direct Keyword Execution
    [Documentation]    Executes two keywords directly.
    ${one}=    Covered Keyword One
    Should Be Equal    ${one}    one
    ${two}=    Covered Keyword Two
    Should Be Equal    ${two}    two

Test Indirect Keyword Execution
    [Documentation]    Executes a keyword indirectly, which still counts
    ...                as covered in the standard aggregate model.
    ${three}=    Call Third Keyword
    Should Be Equal    ${three}    three


*** Keywords ***
Call Third Keyword
    [Documentation]    Local wrapper proving indirect execution is counted.
    ${result}=    Covered Keyword Three
    RETURN    ${result}
