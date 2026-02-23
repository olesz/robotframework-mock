*** Settings ***
Library    DatabaseLibrary
Library    RequestsLibrary
Library    ../../src/mock/MockLibrary.py    DatabaseLibrary    WITH NAME    MockDB
Library    ../../src/mock/MockLibrary.py    RequestsLibrary    WITH NAME    ReqDB
Library    ../../src/mock/MockBuiltin.py    WITH NAME    Bin

*** Test Cases ***
Test Library Mock
    MockDB.Mock Keyword    query    return_value=test_data
    ReqDB.Mock Keyword    post    return_value=test_data_2

    ${result}=    DatabaseLibrary.Query   SELECT * from dummy_table
    Should Be Equal    ${result}    test_data
    ${result}=    RequestsLibrary.POST   alias    url
    Should Be Equal    ${result}    test_data_2

Test BuiltIn Mock
    Bin.Mock Keyword    Convert To Binary    return_value=test_data_3

    ${result}=    Convert To Binary    aaa
    Should Be Equal    ${result}    test_data_3
