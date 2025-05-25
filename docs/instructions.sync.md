
 # list the dropbox accounts and dropbox account files and searches for the accounts in salesforce in batches with a start-from
clear && python -m sync.cmd_migration_analyzer --dropbox-accounts --dropbox-account-files --salesforce-accounts --account-batch-size 5 --start-from 10  2>&1 | tee output.log

# list the dropbox accounts and dropbox account files and searches for the accounts in salesforce and searches for the account files in salesforce in batches with a start-from
clear && python -m salesforce.cmd_fuzzy --dropbox-accounts --dropbox-account-files --salesforce-accounts -salesforce-account-files --account-batch-size 5 --start-from 10  2>&1 | tee output.log


clear && python -m sync.cmd_migration_analyzer --dropbox-accounts-file accounts/fuzzy-small.txt --salesforce-accounts --salesforce-account-files 2>&1 | tee output.log

clear && python -m sync.cmd_migration_analyzer --dropbox-account-name 'Alexander & Armelia Rolle' 2>&1 | tee output.log

clear && python -m sync.cmd_migration_analyzer --dropbox-accounts --batch_size 5 --start-from 10 2>&1 | tee output.log

# list the dropbox accounts only in batches with a start-from
clear && python -m sync.cmd_migration_analyzer --dropbox-accounts --batch_size 5 --start-from 10 --dropbox-accounts-only 2>&1 | tee output.log

# list the dropbox accounts only in batches with a start-from
clear && python -m sync.cmd_migration_analyzer --dropbox-accounts --batch_size 5 --start-from 10 --dropbox-accounts-only 2>&1 | tee output.log

# list the dropbox accounts and dropbox account files in batches with a start-from
clear && python -m sync.cmd_migration_analyzer --dropbox-accounts --dropbox-account-files --account-batch-size 5 --start-from 10  2>&1 | tee output.log



for each dropbox account folder in 'Dropbox account folders list':

                
    Search for the Dropbox account in Salesforce           
      if it has an exact match:
        navigates to the salesforce account and gets the list of all the salesforce account files
        gets the list of account dropbox files, this list should also contain modified date information.
        for each account dropbox file:
            set original_dropbox_filename
            set renamed_dropbox_filename to original_dropbox_filename prefixed with the modified date using format YYMMDD{original_dropbox_filename} if original_dropbox_filename is not already prefixed as 'YYMMDD<filename>' or 'YYMMDD <filename>'
            it searches for renamed_dropbox_filename in the list of salesforce account files
               if it finds it save it in a list
               if it doesn't find it
                   set renamed_dropbox_filename to original_dropbox_filename prefixed with the modified date using format 'YYMMDD {original_dropbox_filename}' if original_dropbox_filename is not already prefixed as 'YYMMDD<filename>' or 'YYMMDD <filename>'
                   search again
               if it does not find it at all save it in a list

      if no exact match for account, print match information

      report all information for each dropbox account and dropbox account files 

        


