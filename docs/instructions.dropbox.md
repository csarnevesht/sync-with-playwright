add new environment variable DROPBOX_SALESFORCE_FOLDER.
Update env.example, src/config.py, src/sync/dropbox_client/utils/config.py with the new environment variable.

add method get_dropbox_salesforce_folder in DropboxClient, and set members:
        self.dropbox_salesforce_folder = dropbox_salesforce_folder 
        self.dropbox_salesforce_path = clean_dropbox_path(dropbox_salesforce_folder) 


