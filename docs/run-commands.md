

# Extract dropbox account app files info and (force) store them in the database
clear && python -m sync.cmd_runner  --dropbox-account-info --commands=extract-dropbox-account-app-files-info,store-in-supabase --continue-on-error --force-store-dropbox-info --dropbox-account-name='Montesino, Maria' 


# Extract info, (force) store in database, analyze
clear && python -m sync.cmd_runner  --dropbox-accounts --dropbox-account-info --salesforce-accounts --salesforce-account-info --commands=extract-dropbox-account-app-files-info,store-in-supabase,analyze-account-data --continue-on-error --force-store-dropbox-info --dropbox-account-name='Montesino, Maria' --keep

# Extract dropbox account info, store, 'Arana, Ada son Luis Arana'
clear && python -m sync.cmd_runner  --dropbox-accounts --dropbox-account-info  --commands=extract-dropbox-account-app-files-info,store-in-supabase --continue-on-error --dropbox-account-name='Arana, Ada son Luis Arana' --keep

# Extract info, analyze 'Montesino, Maria'
clear && python -m sync.cmd_runner  --dropbox-accounts --dropbox-account-info --salesforce-accounts --salesforce-account-info --commands=extract-dropbox-account-app-files-info,store-in-supabase,analyze-account-data --continue-on-error --dropbox-account-name='Montesino, Maria' --keep

# Extract info, store, analyze, copy
clear && python -m sync.cmd_runner  --dropbox-accounts --dropbox-account-info --salesforce-accounts --salesforce-account-info --commands=extract-dropbox-account-app-files-info,store-in-supabase,analyze-account-data,copy-dropbox-account-files-preserve-dates --continue-on-error --keep --force-store-salesforce-info

# Extract info, store, analyze, copy 'Calatayud Zeneida'
clear && python -m sync.cmd_runner  --dropbox-accounts --dropbox-account-info --salesforce-accounts --salesforce-account-info --commands=extract-dropbox-account-app-files-info,store-in-supabase,analyze-account-data,copy-dropbox-account-files-preserve-dates --continue-on-error --keep --force-store-salesforce-info --dropbox-account-name='Calatayud Zeneida'

# Process Salesforce data, store, copy 'Arana, Ada son Luis Arana'
clear && python -m sync.cmd_runner  --dropbox-accounts --dropbox-account-info --salesforce-accounts --salesforce-account-info  --continue-on-error --keep --force-store-salesforce-info --dropbox-account-name="Arana, Ada son Luis Arana" 

# Process Dropbox data, store 'Arana, Ada son Luis Arana'
clear && python -m sync.cmd_runner  --dropbox-accounts --dropbox-account-info --continue-on-error --keep --commands=extract-dropbox-account-app-files-info,store-in-supabase,analyze-account-data --dropbox-account-name="Arana, Ada son Luis Arana" 

# store dropbox account info from log app files
clear && python -m src.sync.commands.process_log_app_files --log-dir logs/2025-06-25_02-26-00  2>&1 | tee logs/process_log_app_files.log