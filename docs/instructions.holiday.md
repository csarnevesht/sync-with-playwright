add new environment variable DROPBOX_HOLIDAY_FOLDER.
Update env.example, src/config.py, src/sync/dropbox_client/utils/config.py with the new environment variable.

add method get_dropbox_holiday_folder in DropboxClient, and set members:
        self.dropbox_holiday_folder = dropbox_holiday_folder 
        self.dropbox_holiday_path = clean_dropbox_path(dropbox_holiday_folder) 


add method get_dropbox_holiday_file in DropboxClient to take agument holiday_file with default value 'HOLIDAY_CLIENT_LIST'
This method should set member self.dropbox_holiday_file and if it's set, return it, if not, get the file.

add method get_dropbox_account_info in DropboxClient 

    def get_dropbox_account_info(self, account_folder: str) -> Dict[str, str]:



