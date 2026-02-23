*** Settings ***
Library    DatabaseLibrary
Library    MockLibrary    DatabaseLibrary    WITH NAME    MockDB

*** Test Cases ***
Example Test With Mock
    # Mock a keyword
    MockDB.Mock Keyword    query    return_value=test_data
    
    # Call the mocked keyword
    ${result}=    DatabaseLibrary.Query    SELECT * FROM users
    
    # Verify the result
    Should Be Equal    ${result}    test_data
    
    # Verify it was called
    MockDB.Verify Keyword Called    query    times=1
    
    # Clean up
    MockDB.Reset Mocks
