*** Settings ***
Documentation     User Acceptance Tests for WebUI Settings Persistence
...               These tests verify that user settings changes through the web interface
...               are properly saved to the database and persist across page reloads.
...
...               Bug Context: Settings submitted via the web form were not persisting
...               to the database when changing db_type from sqlite to postgresql.
...
...               Test Strategy:
...               - Test the actual user workflow through the WebUI
...               - Verify settings persist after page reload
...               - Test both boolean and string settings
...               - Test the specific bug scenario (sqlite -> postgresql)

Library           SeleniumLibrary
Library           OperatingSystem
Library           String
Library           Collections

Suite Setup       Setup Test Suite
Suite Teardown    Teardown Test Suite
Test Setup        Open Browser To Settings Page
Test Teardown     Close Browser

*** Variables ***
${SERVER}         127.0.0.1:5001
${BASE_URL}       http://${SERVER}
${BROWSER}        Firefox
${DELAY}          0.5
${SETTINGS_URL}   ${BASE_URL}/opts
${SAVE_WAIT}      5s

*** Test Cases ***

Test Settings Page Loads
    [Documentation]    Verify that the settings page loads correctly
    [Tags]    smoke
    Page Should Contain Element    id:btn-save-changes
    Page Should Contain Element    id:allopts
    Page Should Contain Element    id:token
    Page Should Contain    Settings

Test Database Type Change From SQLite To PostgreSQL Persists
    [Documentation]    Test the EXACT bug scenario that was reported
    ...                1. User changes db_type from sqlite to postgresql
    ...                2. User enters PostgreSQL connection details
    ...                3. User clicks save
    ...                4. Page reloads showing success
    ...                5. Settings should still show PostgreSQL configuration
    [Tags]    critical    regression    bug-fix

    # Navigate to the storage module settings
    Click Storage Module Tab

    # Verify current db_type (should be sqlite by default)
    ${initial_db_type}=    Get Selected List Label    id:sfp__stor_db:db_type
    Log    Initial DB Type: ${initial_db_type}

    # Change database type to PostgreSQL
    Select From List By Label    id:sfp__stor_db:db_type    postgresql

    # Enter PostgreSQL connection details
    Input Text    id:sfp__stor_db:postgresql_host    unified-postgres
    Input Text    id:sfp__stor_db:postgresql_port    5432
    Input Text    id:sfp__stor_db:postgresql_database    spiderfoot_db
    Input Text    id:sfp__stor_db:postgresql_username    postgres
    Input Text    id:sfp__stor_db:postgresql_password    password123

    # Save settings
    Click Button    id:btn-save-changes

    # Wait for redirect to complete (should go to /opts?updated=1)
    Wait Until Location Contains    opts?updated=1    timeout=${SAVE_WAIT}
    Wait Until Page Contains Element    id:btn-save-changes

    # Navigate back to storage module tab
    Click Storage Module Tab

    # Verify settings persisted - THIS IS THE BUG TEST
    ${saved_db_type}=    Get Selected List Label    id:sfp__stor_db:db_type
    Should Be Equal As Strings    ${saved_db_type}    postgresql
    ...    msg=Database type did not persist after save! Bug is present.

    ${saved_host}=    Get Value    id:sfp__stor_db:postgresql_host
    Should Be Equal As Strings    ${saved_host}    unified-postgres

    ${saved_port}=    Get Value    id:sfp__stor_db:postgresql_port
    Should Be Equal As Strings    ${saved_port}    5432

    ${saved_database}=    Get Value    id:sfp__stor_db:postgresql_database
    Should Be Equal As Strings    ${saved_database}    spiderfoot_db

    ${saved_username}=    Get Value    id:sfp__stor_db:postgresql_username
    Should Be Equal As Strings    ${saved_username}    postgres

Test Boolean Settings Persist Correctly
    [Documentation]    Test that boolean settings (checkboxes/selects) are properly
    ...                saved and restored. The bug involved booleans not being
    ...                converted to "1"/"0" strings before database storage.
    [Tags]    critical    regression    boolean

    # Navigate to storage module
    Click Storage Module Tab

    # Find boolean settings (they render as select dropdowns with True/False options)
    # Example: enable_connection_pooling, enable_auto_recovery
    ${initial_pooling}=    Get Selected List Label    id:sfp__stor_db:enable_connection_pooling
    Log    Initial connection pooling: ${initial_pooling}

    # Toggle the boolean setting
    ${new_pooling_value}=    Set Variable If    '${initial_pooling}'=='True'    False    True
    Select From List By Label    id:sfp__stor_db:enable_connection_pooling    ${new_pooling_value}

    # Save settings
    Click Button    id:btn-save-changes
    Wait Until Location Contains    opts?updated=1    timeout=${SAVE_WAIT}
    Wait Until Page Contains Element    id:btn-save-changes

    # Navigate back to storage module
    Click Storage Module Tab

    # Verify boolean persisted correctly
    ${saved_pooling}=    Get Selected List Label    id:sfp__stor_db:enable_connection_pooling
    Should Be Equal As Strings    ${saved_pooling}    ${new_pooling_value}
    ...    msg=Boolean setting did not persist correctly!

Test Mixed Boolean And String Settings Persist Together
    [Documentation]    Test that when user changes both boolean and string settings
    ...                in a single form submission, both types persist correctly.
    ...                This tests the complete fix scenario.
    [Tags]    critical    regression    mixed-types

    Click Storage Module Tab

    # Change database type (string)
    Select From List By Label    id:sfp__stor_db:db_type    postgresql
    Input Text    id:sfp__stor_db:postgresql_host    test.database.local
    Input Text    id:sfp__stor_db:postgresql_port    5433

    # Change boolean settings
    Select From List By Label    id:sfp__stor_db:enable_connection_pooling    True
    Select From List By Label    id:sfp__stor_db:enable_auto_recovery    False

    # Save all changes
    Click Button    id:btn-save-changes
    Wait Until Location Contains    opts?updated=1    timeout=${SAVE_WAIT}
    Wait Until Page Contains Element    id:btn-save-changes

    # Reload and verify
    Click Storage Module Tab

    # Verify string settings
    ${saved_db_type}=    Get Selected List Label    id:sfp__stor_db:db_type
    Should Be Equal As Strings    ${saved_db_type}    postgresql

    ${saved_host}=    Get Value    id:sfp__stor_db:postgresql_host
    Should Be Equal As Strings    ${saved_host}    test.database.local

    ${saved_port}=    Get Value    id:sfp__stor_db:postgresql_port
    Should Be Equal As Strings    ${saved_port}    5433

    # Verify boolean settings
    ${saved_pooling}=    Get Selected List Label    id:sfp__stor_db:enable_connection_pooling
    Should Be Equal As Strings    ${saved_pooling}    True

    ${saved_recovery}=    Get Selected List Label    id:sfp__stor_db:enable_auto_recovery
    Should Be Equal As Strings    ${saved_recovery}    False

Test Settings Persist Across Browser Session
    [Documentation]    Simulate a complete browser restart by closing and reopening
    ...                the browser, then verifying settings are still present.
    ...                This ensures settings are truly in the database, not just memory.
    [Tags]    regression    persistence

    Click Storage Module Tab

    # Set unique identifiable values
    ${test_host}=    Generate Random String    12    [LETTERS][NUMBERS]
    ${test_host_full}=    Set Variable    test-${test_host}.example.com

    Select From List By Label    id:sfp__stor_db:db_type    postgresql
    Input Text    id:sfp__stor_db:postgresql_host    ${test_host_full}
    Input Text    id:sfp__stor_db:postgresql_port    6543

    # Save
    Click Button    id:btn-save-changes
    Wait Until Location Contains    opts?updated=1    timeout=${SAVE_WAIT}

    # Close browser completely (simulate session end)
    Close Browser

    # Reopen browser and navigate to settings (simulate new session)
    Open Browser To Settings Page
    Click Storage Module Tab

    # Verify settings survived the "restart"
    ${saved_db_type}=    Get Selected List Label    id:sfp__stor_db:db_type
    Should Be Equal As Strings    ${saved_db_type}    postgresql

    ${saved_host}=    Get Value    id:sfp__stor_db:postgresql_host
    Should Be Equal As Strings    ${saved_host}    ${test_host_full}
    ...    msg=Settings did not persist across browser session!

Test Global Boolean Settings Persist
    [Documentation]    Test that global (not module-specific) boolean settings
    ...                also persist correctly with the fix
    [Tags]    regression    global

    # Should be on Global tab by default
    Page Should Contain Element    id:_debug

    # Get current debug setting
    ${initial_debug}=    Get Selected List Label    id:_debug
    Log    Initial debug setting: ${initial_debug}

    # Toggle it
    ${new_debug_value}=    Set Variable If    '${initial_debug}'=='True'    False    True
    Select From List By Label    id:_debug    ${new_debug_value}

    # Save
    Click Button    id:btn-save-changes
    Wait Until Location Contains    opts?updated=1    timeout=${SAVE_WAIT}
    Wait Until Page Contains Element    id:btn-save-changes

    # Verify (should still be on Global tab)
    ${saved_debug}=    Get Selected List Label    id:_debug
    Should Be Equal As Strings    ${saved_debug}    ${new_debug_value}
    ...    msg=Global boolean setting did not persist!

Test Settings Form Submission Returns Success
    [Documentation]    Verify that the form submission returns HTTP 200/redirect
    ...                This was always working, but we verify it here for completeness
    [Tags]    smoke

    Click Storage Module Tab
    Input Text    id:sfp__stor_db:postgresql_host    testhost
    Click Button    id:btn-save-changes

    # Should redirect to success page
    Wait Until Location Contains    opts?updated=1    timeout=${SAVE_WAIT}
    Location Should Contain    /opts

    # Page should show updated parameter
    ${url}=    Get Location
    Should Contain    ${url}    updated=1

Test CSRF Token Present In Form
    [Documentation]    Verify that CSRF protection is in place
    [Tags]    security

    Page Should Contain Element    id:token
    ${token_value}=    Get Value    id:token
    Should Not Be Empty    ${token_value}
    Log    CSRF Token present: ${token_value}

Test Multiple Sequential Saves
    [Documentation]    Test that multiple saves in sequence all persist correctly
    ...                This catches any state management issues
    [Tags]    regression    stress

    Click Storage Module Tab

    # First save
    Input Text    id:sfp__stor_db:postgresql_host    host1
    Click Button    id:btn-save-changes
    Wait Until Location Contains    opts?updated=1    timeout=${SAVE_WAIT}
    Wait Until Page Contains Element    id:btn-save-changes

    # Second save
    Click Storage Module Tab
    Clear Element Text    id:sfp__stor_db:postgresql_host
    Input Text    id:sfp__stor_db:postgresql_host    host2
    Click Button    id:btn-save-changes
    Wait Until Location Contains    opts?updated=1    timeout=${SAVE_WAIT}
    Wait Until Page Contains Element    id:btn-save-changes

    # Third save
    Click Storage Module Tab
    Clear Element Text    id:sfp__stor_db:postgresql_host
    Input Text    id:sfp__stor_db:postgresql_host    host3
    Click Button    id:btn-save-changes
    Wait Until Location Contains    opts?updated=1    timeout=${SAVE_WAIT}
    Wait Until Page Contains Element    id:btn-save-changes

    # Verify final value
    Click Storage Module Tab
    ${final_host}=    Get Value    id:sfp__stor_db:postgresql_host
    Should Be Equal As Strings    ${final_host}    host3
    ...    msg=Multiple sequential saves did not persist correctly!

*** Keywords ***

Setup Test Suite
    [Documentation]    Setup that runs once before all tests
    Log    Starting SpiderFoot WebUI Settings Persistence Tests
    Log    Server: ${BASE_URL}
    Log    Browser: ${BROWSER}
    Set Selenium Speed    ${DELAY}

Teardown Test Suite
    [Documentation]    Cleanup that runs once after all tests
    Log    Completed SpiderFoot WebUI Settings Persistence Tests
    Close All Browsers

Open Browser To Settings Page
    [Documentation]    Open browser and navigate to settings page
    Open Browser    ${SETTINGS_URL}    ${BROWSER}
    Maximize Browser Window
    Wait Until Page Contains Element    id:btn-save-changes    timeout=10s
    Title Should Be    SpiderFoot

Click Storage Module Tab
    [Documentation]    Navigate to the sfp__stor_db module settings tab
    Wait Until Page Contains Element    id:tab_sfp__stor_db    timeout=10s
    Click Element    id:tab_sfp__stor_db
    Wait Until Element Is Visible    id:optsect_sfp__stor_db    timeout=5s
    # Give JavaScript time to render the tab
    Sleep    0.5s
