write a test called test_account_account_files in tests which 

- search for account "Beth Albert" in Salesforce CRM
          - if it finds the Salesforce CRM account:
                - navigate to the Salesforce CRM account files (using    account_manager.navigate_to_files_and_get_number_of_files_for_this_account)
          - gets a list of all the file names for the account