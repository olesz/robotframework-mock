*** Settings ***
Documentation    Demo resource used to exercise MockCoverage. Three of the four
...              keywords below are executed by coverage-tests.robot, giving
...              75% keyword coverage.


*** Keywords ***
Covered Keyword One
    [Documentation]    Executed by the coverage test suite.
    RETURN    one

Covered Keyword Two
    [Documentation]    Executed by the coverage test suite.
    RETURN    two

Covered Keyword Three
    [Documentation]    Executed indirectly via another keyword.
    RETURN    three

Uncovered Keyword
    [Documentation]    Never executed - shows up as missed coverage.
    RETURN    never
