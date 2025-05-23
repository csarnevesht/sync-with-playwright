
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=./chrome-debug-profile &

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9223 --user-data-dir=./chrome-debug-profile &

run is as follows:

clear && python main.py 2>&1 | tee output.log


clear && python -m tests.test_all 2>&1 | tee output.log

clear && python -m tests.test_accounts_query 2>&1 | tee output.log


clear && python -m salesforce.cmd_fuzzy 2>&1 | tee output.log

clear && python -m dropbox_renamer.cmd_rename 2>&1 | tee output.log

clear && python -m dropbox_renamer.cmd_analyze --accounts-file accounts/small.txt 2>&1 | tee output.log



curl -X POST https://api.dropboxapi.com/2/files/list_folder \
  --header 'Authorization: Bearer token' \
  --header 'Content-Type: application/json' \
  --data '{"path":"/A Work Documents/A WORK Documents/Principal Protection","include_mounted_folders":true}'

curl -X POST https://api.dropboxapi.com/2/files/list_folder/continue \
  --header 'Authorization: Bearer token' \
  --header 'Content-Type: application/json' \
  --data '{"cursor": "cursor from previous api output"}'