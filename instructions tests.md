write a test called test_account_account_files in tests which 

- search for account "Beth Albert" in Salesforce CRM
          - if it finds the Salesforce CRM account:
                - navigate to the Salesforce CRM account files (using    account_manager.navigate_to_files_and_get_number_of_files_for_this_account)
          - gets a list of all the file names for the account


 write a test test_account_file_delete which:
- searches for John Smith account, 
     - if it doesn't find it create it (See test_accounts_create.py) 
     - if it finds the Salesforce CRM account:
                - navigate to the Salesforce CRM account files (using    account_manager.navigate_to_files_and_get_number_of_files_for_this_account)
          - gets a list of all the file names for the account
          - deletes the first file