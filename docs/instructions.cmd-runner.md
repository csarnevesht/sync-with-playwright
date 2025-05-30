

create a command runner class in src/sync/command_runner.py which takes args which have already been parsed by src/sync/cmd_runner.py
     args: Command line arguments containing all options

It specifically it interprets and executes the following command args:

     --commands='rename-account-files,delete-account,create-account'
     or 
     --commands-file='commands/commands.txt'

commands:
    rename-dropbox-account-files
    rename-dropbox-account-file
    delete-salesforce-account
    create-salesforce-account
    delete-salesforce-account-file
    upload-salesforce-account-file
    upload-salesforce-account-files
    download-salesforce-account-file


From src/sync/cmd_runner.py run_command(args) I want to be able to call some method which will allow me to execute those commands.


An example of how I will call cmd_runner.py follows:
Description: (Re)Create account 'Matalon, Dennis' in Salesforce

clear && python -m sync.cmd_runner \
  --dropbox-accounts \
  --dropbox-account-files \
  --salesforce-accounts \
  --salesforce-account-files \
  --commands='rename-dropbox-account-files,delete-salesforce-account,create-salesforce-account' \
  --dropbox-account-name='Matalon, Dennis'


commands/commands.txt
rename-dropbox-account-files
delete-salesforce-account
create-salesforce-account
upload-salesforce-account-files








