

Write sync code which synchronizes data from Dropbox to Salesforce CRM.

To get the Dropbox data use the dropbox apis via an api token.
To access Salesforce CRM we don't have access to the apis so we will use playwright instead. 
Also, we can only log in once to the Salesforce CRM.
We want to use the Chrome browser only since we are already logged in (we don't want to use a new incognito browser page).
For the playwright code we want to use page objects.

## Setup:
For Dropbox access use token.txt
Provide interactive prompt if token is missing.
Prompt the user with the Dropbox root folder (default: "Wealth Management").
Prompt the user for Salesforce CRM url (default: is https://capitalprotect.lightning.force.com)
For Salesforce CRM use the Chrome browser provided by user where the user has already been logged in.

## Dropbox integration:
Connect to Dropbox using the provided token
Allow user to specify a root folder 
Each folder under the root folder represents an account with 'account name'.  Typically the account folder consists of the first word representing the first name, and the last word representing the last name. If there are more than two words, what's in the middle represents the middle name.
In each account folder there are files for the account. 
    - account info file with pattern *App.pdf contains more information about the account holder including: 
            - Date of Birth, Age
            - Sex
            - SSN
            - Contact Information (email, phone, address, city, state, zip)
            Note: make the pattern configurable (in .env file)
    - driver's license: file with pattern *DL.jpeg
            Note: make the pattern configurable (in .env file)

## Dropbox file processing:
Each account folder in the Dropbox root folder has account files.  
Account information is typically stored in a file with pattern *App.pdf.
            Specific fields like:
                - Date of Birth, Age
                - Sex
                - SSN
                - Contact Information (email, phone, address, city, state, zip)
Driver's license is typically stored in a file with pattern *DL.jpeg.
                - use ocr to extract information and store it in customer information object

## Dropbox to Salesforce CRM integration using playwright 
For each Dropbox account folder with 'account name'
    - In Salesforce, navigate to Accounts page via Accounts tab
    - search for the account 
        - if the account is not found, then create a new Client account
            - Extract account information from files in Dropbox if it exists
            - Enter "First Name", "Last Name", and "Middle Name" if it exists.
            - Enter other data if it exists.
        - if the account is found, click on the Account Name (first column of first row) and synchronize the account files from Dropbox to Salesforce:
            - go to the account by clicking on the Account
            - go to the account's Files by clicking on "Files"
            - search for <number_of_items> items.*Sorted by Last Modified, extract the number in number_of_items
                - if number_of_items is 0:
                     - add the Dropbox files to this Salesforce account. 
                        - Download the Dropbox account folder with files
                        - click "Add Files" (Salesforce)
                        - click "Upload Files" (Salesforce)
                        - click on account folder and select all files, click "Done"

                - if number_of_items > 0:
                    - search for the Dropbox files in the Accounts File page:
                        Note: the Salesforce page may have a date prefix, so do a pattern search for the file name instead. 
                        For example: 
                            DropBox file: Ron Albert 100k Check GILICO.pdf'
                            Search for: *Ron Albert 100k Check GILICO
                        - If the file is found, keep that file in a list of found_files, else keep that file in list of files_to_add.
                    - if files_to_add is not empty then upload them:
                          create local folder with account name
                        - for each file in files_to_add:
                               - download the file from Dropbox to the local folder and rename it with its modification date 
                                 Example:
                                   'Adam Smith info.pdf' -> '20240501 Adam Smith info.pdf'
                        - click on (Salesforce) "Add Files" then "Upload Files" (in dialog box), click on the local folder with account name, select all files click "Open".








NEVER NEVER NEVER kill the browser!!!!

run is as follows:

clear && python main.py 2>&1 | tee output.log

python -m tests.test_all
