add new environment variable DROPBOX_HOLIDAY_FOLDER.
Update env.example, src/config.py, src/sync/dropbox_client/utils/config.py with the new environment variable.

add method get_dropbox_holiday_folder in DropboxClient, and set members:
        self.dropbox_holiday_folder = dropbox_holiday_folder 
        self.dropbox_holiday_path = clean_dropbox_path(dropbox_holiday_folder) 


add method get_dropbox_holiday_file in DropboxClient to take agument holiday_file with default value 'HOLIDAY_CLIENT_LIST'
This method should set member self.dropbox_holiday_file and if it's set, return it, if not, get the file.

add method get_dropbox_account_info in DropboxClient and implement it

    def get_dropbox_account_info(self, account_name: str) -> Dict[str, str]:
        """Get account information for account_name from the (holiday) account info file.
        
        This method searches for and processes an account in the (holiday) account info file. 
        It extracts key personal information such as name, address, phone number, and email.
        
        The method follows these steps:
        1. Locates the (holiday) account info file
        2. Extracts text content from the XLSX
        3. Parses the text to find specific information fields
        4. Returns a dictionary of found information
        
        Args:
            account_name (str): The name of the account to search for in the (holiday) account info file
            
        Returns:
            Dict[str, str]: A dictionary containing extracted account information with the following keys:
                - name (str): Full name of the account holder
                - address (str): Physical address
                - phone (str): Contact phone number
                - email (str): Email address
                
            Returns an empty dictionary if:
                - No account info file is found
                - File cannot be downloaded
                - Text extraction fails
                - No information can be parsed from the text
                
        Raises:
            Exception: Any error during the extraction process is caught and logged
            
        Example:
            >>> client = DropboxClient(token)
            >>> info = client.get_dropbox_account_info("John Smith")
            >>> print(info)
            {
                'name': 'John Smith',
                'address': '123 Main St, New York, NY 10001',
                'phone': '(555) 123-4567',
                'email': 'john.smith@example.com'
            }
        """
        try:
            account_info = {}
                
            return account_info

        except Exception as e:
            logging.error(f"Error getting account info for {account_name}: {e}")
            return {}



