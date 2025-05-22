
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=./chrome-debug-profile &

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9223 --user-data-dir=./chrome-debug-profile &

run is as follows:

clear && python main.py 2>&1 | tee output.log

clear && python test_upload.py 2>&1 | tee output.log

clear && python test_accounts_query.py 2>&1 | tee output.log

clear && python test_account_search.py 2>&1 | tee output.log
