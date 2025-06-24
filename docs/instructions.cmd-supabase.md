

    find dropbox account folder in supabase
    get all applications for the dropbox account 
        get the actual application from dropbox
            extract first name, last name, etc from the application file and update the database record for the application




    find dropbox account folder in supabase
    get all applications and all data (first_name, last name, dob, gender, etc)
    loop through all updated applications and create a best guess for household name, household head, household member(s)



dropbox_account_folder
    dropbox_account_application_files
          dropbox_account_application_info
    dropbox_account [source dropbox_client_list]
    dropbox_account [source dropbox_aplication_files]
    salesforce_account [owner]
    salesforce_account [joint_owner]
