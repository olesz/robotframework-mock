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
