List of account folder names in accounts/fuzzy.txt



Write a test accounts_fuzzy_search that does the following:
Iterates through the above list of account folder names
For each item, determine the last name.
Then search for the last name in Salesforce CRM
   - see if you can use account_manager.get_accounts_matching_condition, with view_name: str = "All Accounts"

Let's change that to dropbox account folders.
If we use option --all flag, it will process all dropbox account folders except those listed in ingored folders currently listed in accounts/ignore.txt.
If we don't use option --all, it will get the dropbox account folders from accounts/main.txt.
If we use option --accounts-file ACCOUNTS_FILE then we will use the list of dropbox accounts from ACCOUNTS_FILE
