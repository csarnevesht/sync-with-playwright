/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=./chrome-debug-profile &

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9223 --user-data-dir=./chrome-debug-profile &

run it as follows:

clear && PYTHONPATH=src python -m sync.dropbox_client.cmd_analyze --help

clear && python main.py 2>&1 | tee output.log


clear && python -m tests.test_all 2>&1 | tee output.log

*** issues
clear && python -m tests.test_accounts_query 2>&1 | tee output.log

clear && python -m tests.test_account_files 2>&1 | tee output.log

clear && python -m dropbox_client.cmd_rename 2>&1 | tee output.log

clear && python -m dropbox_client.cmd_analyze --accounts-file accounts/fuzzy-small.txt 2>&1 | tee output.log

# list all dropbox account folders
clear && python -m dropbox_client.cmd_analyze --show-all --folders-only

# list all dropbox account folders and files
clear && python -m dropbox.cmd_analyze --show-all 

clear && python -m sync.cmd_analyzer --dropbox-accounts --dropbox-account-files --salesforce-accounts --account-batch-size 5 --start-from 10  2>&1 | tee output.log

clear && python -m sync.cmd_analyzer --dropbox-accounts-file accounts/fuzzy-small.txt --salesforce-accounts --salesforce-account-files 2>&1 | tee output.log

clear && python -m sync.cmd_analyzer --dropbox-account-name 'Alexander & Armelia Rolle' 2>&1 | tee output.log

clear && python -m sync.cmd_analyzer --dropbox-accounts --batch_size 5 --start-from 10 2>&1 | tee output.log

clear && python -m sync.cmd_analyzer \
    --dropbox-accounts \
    --dropbox-account-files \
    --salesforce-accounts \
    --salesforce-account-files \
    --account-batch-size 5 \
    --start-from 0 \
    2>&1 | tee output.log

clear && python -m sync.cmd_analyzer \
    --dropbox-account-name='Matalon, Dennis' \
    --dropbox-account-files \
    --salesforce-accounts \
    --salesforce-account-files \
    2>&1 | tee output.log

# list the dropbox accounts only in batches with a start-from
clear && python -m sync.cmd_analyzer --dropbox-accounts --batch_size 5 --start-from 10 --dropbox-accounts-only 2>&1 | tee output.log

# list the dropbox accounts and dropbox account files in batches with a start-from
clear && python -m sync.cmd_analyzer --dropbox-accounts --dropbox-account-files --account-batch-size 5 --start-from 10  2>&1 | tee output.log

curl -X POST https://api.dropboxapi.com/2/files/list_folder \
  --header 'Authorization: Bearer token' \
  --header 'Content-Type: application/json' \
  --data '{"path":"/A Work Documents/A WORK Documents/Principal Protection","include_mounted_folders":true}'

curl -X POST https://api.dropboxapi.com/2/files/list_folder/continue \
  --header 'Authorization: Bearer token' \
  --header 'Content-Type: application/json' \
  --data '{"cursor": "cursor from previous api output"}'

from InquirerPy import inquirer

desc = inquirer.text(message="Enter description:").execute()
print("You entered:", desc)



unset DROPBOX_TOKEN && clear && python -m sync.cmd_runner  --salesforce-accounts --dropbox-account-info --dropbox-accounts

unset DROPBOX_TOKEN && clear && python -m sync.cmd_runner  --salesforce-accounts --dropbox-account-info --dropbox-accounts --dropbox-accounts-file='accounts/relationships.txt'

#household 
unset DROPBOX_TOKEN && clear && python -m sync.cmd_runner --salesforce-accounts --dropbox-account-info --dropbox-accounts --salesforce-account-info --dropbox-account-name='Aspillaga, Jose'