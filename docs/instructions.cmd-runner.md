

create a command runner class in src/sync/command_runner.py which takes args which have already been parsed by src/sync/cmd_runner.py
     args: Command line arguments containing all options

It specifically it interprets and executes the following command args:

     --commands='prefix-account-files,delete-account,create-account'
     or 
     --commands-file='commands/commands.txt'

commands:
    prefix-dropbox-account-files
    prefix-dropbox-account-file
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
  --commands='prefix-dropbox-account-files,delete-salesforce-account,create-salesforce-account' \
  --dropbox-account-name='Matalon, Dennis'


commands/commands.txt
prefix-dropbox-account-files
delete-salesforce-account
create-salesforce-account
upload-salesforce-account-files





for CommandRunner, most of the commands will need the following arguments:
DropboxClient
browser, page = get_salesforce_page(p)
account_manager
file_manager

I would like to be able to do:
command_runner = CommandRunner(args)
command_runner.setContext(dropbox_client)
command_runner.setData(dropbox_account_info)

for CommandRunner method _prefix_dropbox_account_files the following is needed:
dropbox_client = self.getContext('dropbox_client')
dropbox_account_info = self.getContext('dropbox_account_info')
dropbox_account_folders = self.getContext('dropbox_account_folders')


help me implement this method.
Reusing as many methods from src/sync/dropbox_client/utils/dropbox_utils.py

CommandRunner _prefix_dropbox_account_files should:
            dropbox_client = self.get_context('dropbox_client')
            dropbox_root_folder = dropbox_client.get_dropbox_root_folder()
            dropbox_account_info = self.get_data('dropbox_account_info')
            dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
            dropbox_salesforce_folder = dropbox_client.get_dropbox_salesforce_folder()

            # TODO: 
            verify that dropbox_account_folder_name exists in dropbox 
            rename it with its modification date if it doesn't already have a date prefix