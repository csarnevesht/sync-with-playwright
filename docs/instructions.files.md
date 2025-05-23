List of account folder names:
Smith, John & Sarah
Johnson, Michael (Medicaid Mike)
Williams, David (Medicaid Mike)
Brown, Lisa (Medicaid Mike)
Davis, Robert Daughter Emily (Medicaid Mike)
Miller, Thomas & Daughter Grace Wilson (Medicaid Mike)
Taylor, Jennifer daughter Olivia Parker
Anderson, Elizabeth son William Anderson IV
Martinez, Sofia (Mike)
Thompson, Richard nephew James Wilson
Wilson, Peter & Maria
Robinson, Patricia daughter Laura Clark
Garcia, Theresa (Mike)
Moore, Daniel and Rachel
Lee, Victoria
Walker, Susan
Clark, Andrew (Mike)
Lewis, Margaret sons John and Michael
Hall, Paul daughter Martinez
Allen, Sophia
Young, George (Mike)
King, Frances daughter Patricia White
Wright, Katherine
Scott, Donald
Green, Maria 


Write a test test_accounts_fuzzy_find that does the following:
Iterates through the above list of account folder names
For each item, determine the last name.
Then search for the last name in Salesforce CRM
   - see if you can use account_manager.get_accounts_matching_condition, with drop_down_option_text: str = "All Accounts"

Let's change that to dropbox account folders.
If we use option --all flag, it will process all dropbox account folders except those listed in ingored folders currently listed in accounts/ignore.txt.
If we don't use option --all, it will get the dropbox account folders from accounts/main.txt.
If we use option --accounts-file ACCOUNTS_FILE then we will use the list of dropbox accounts from ACCOUNTS_FILE
