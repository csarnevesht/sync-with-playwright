
create sync/cmd_cp.py which is similar to sync/cmd_ping.py but what it does differently is:
- it launches a browser with remote debugging.
- and it goes to url specified in SALESFORCE_URL as set in .env.

Make sure to reuse code that has already been implemented for sync/cmd_ping.py and sync/comd_analyzer.py.



i want to create an installer which does all of this.  Can you do this?
I don't want to manually specify the chrome_extension directory. It should be done by the installer. 
then generate the code which allows the chrome_extension directory.


ok, now let's work on an installer and packager for macos and windows, which includes the chrome_extension, and all the python code.
The installer should:
- 