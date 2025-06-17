"""
Command Runner for Sync Operations

This module provides a CommandRunner class that executes various sync operations
between Dropbox and Salesforce, such as renaming files, creating/deleting accounts,
and managing account files.
"""

import glob
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import dropbox
import os
import tempfile
import re
import fnmatch
import time

from sync.dropbox_client.utils.dropbox_utils import get_renamed_path, list_dropbox_folder_contents
from sync.dropbox_client.utils.file_utils import log_renamed_file
from sync.dropbox_client.utils.logging_utils import log_dropbox_app_file_info
from sync.salesforce_client.utils.file_upload import upload_account_file, upload_account_file_with_retries

class CommandRunner:
    """Handles execution of sync commands between Dropbox and Salesforce."""
    
    def __init__(self, args):
        """Initialize the command runner with parsed arguments.
        
        Args:
            args: Command line arguments containing all options
        """
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.report_logger = logging.getLogger('report')
        self.summary_logger = logging.getLogger('summary')
        
        # Initialize context and data storage
        self._context: Dict[str, Any] = {}
        self._data: Dict[str, Any] = {}
        
        # Log initialization
        self.logger.info("Initializing CommandRunner")
        self.report_logger.info("\n=== COMMAND RUNNER INITIALIZED ===")
        
        # Log command source
        if args.commands:
            self.logger.info(f"Commands specified via --commands: {args.commands}")
            self.report_logger.info(f"Commands from --commands: {args.commands}")
        elif args.commands_file:
            self.logger.info(f"Commands file specified: {args.commands_file}")
            self.report_logger.info(f"Commands from file: {args.commands_file}")
        
        # Log account name if specified
        if args.dropbox_account_name:
            self.logger.info(f"Target Dropbox account: {args.dropbox_account_name}")
            self.report_logger.info(f"Target Dropbox account: {args.dropbox_account_name}")

    
    def set_context(self, key: str, value: Any) -> None:
        """Set a context value.
        
        Args:
            key: The context key
            value: The context value
        """
        self._context[key] = value
        self.logger.debug(f"Set context '{key}'")
    
    def get_context(self, key: str) -> Any:
        """Get a context value.
        
        Args:
            key: The context key to retrieve
            
        Returns:
            The context value
            
        Raises:
            KeyError: If the context key doesn't exist
        """
        if key not in self._context:
            raise KeyError(f"Context key '{key}' not found")
        return self._context[key]
    
    def set_data(self, key: str, value: Any) -> None:
        """Set a data value.
        
        Args:
            key: The data key
            value: The data value
        """
        self._data[key] = value
        self.logger.debug(f"Set data {key}: {value}")
    
    def get_data(self, key: str) -> Any:
        """Get a data value.
        
        Args:
            key: The data key to retrieve
            
        Returns:
            The data value
            
        Raises:
            KeyError: If the data key doesn't exist
        """
        if key not in self._data:
            raise KeyError(f"Data key '{key}' not found")
        return self._data[key]
    
    def _get_commands(self) -> List[str]:
        """Get the list of commands to execute from either --commands or --commands-file.
        
        Returns:
            List[str]: List of commands to execute
        """
        commands = []
        if self.args.commands:
            commands = [cmd.strip() for cmd in self.args.commands.split(',')]
            self.logger.info(f"Parsed {len(commands)} commands from --commands argument")
        elif self.args.commands_file:
            try:
                with open(self.args.commands_file, 'r') as f:
                    commands = [line.strip() for line in f if line.strip()]
                self.logger.info(f"Successfully read {len(commands)} commands from file: {self.args.commands_file}")
            except Exception as e:
                self.logger.error(f"Error reading commands file {self.args.commands_file}: {str(e)}")
                self.report_logger.info(f"Error reading commands file {self.args.commands_file}: {str(e)}")
                raise
        
        if not commands:
            self.logger.warning("No commands found to execute")
            self.report_logger.info("No commands found to execute")
        else:
            self.logger.info("Commands to execute:")
            self.report_logger.info("\nCommands to execute:")
            for i, cmd in enumerate(commands, 1):
                self.logger.info(f"  {i}. {cmd}")
                self.report_logger.info(f"  {i}. {cmd}")
        
        return commands
    
    def execute_commands(self) -> None:
        """Execute all specified commands in sequence."""
        start_time = datetime.now()
        self.logger.info("Starting command execution")
        self.report_logger.info("\n=== STARTING COMMAND EXECUTION ===")
        
        commands = self._get_commands()
        if not commands:
            self.logger.warning("No commands specified to execute")
            self.report_logger.info("No commands specified to execute")
            return
        
        total_commands = len(commands)
        successful_commands = 0
        failed_commands = 0
        
        for index, command in enumerate(commands, 1):
            try:
                self.logger.info(f"[{index}/{total_commands}] Executing command: {command}")
                self.report_logger.info(f"\n[{index}/{total_commands}] Executing command: {command}")
                
                command_start_time = datetime.now()
                self._execute_single_command(command)
                command_duration = datetime.now() - command_start_time
                
                self.logger.info(f"Command completed successfully in {command_duration}")
                self.report_logger.info(f"Command completed successfully in {command_duration}")
                successful_commands += 1
                
            except Exception as e:
                self.logger.error(f"Error executing command {command}: {str(e)}")
                self.report_logger.info(f"Error executing command {command}: {str(e)}")
                failed_commands += 1
                
                if not self.args.continue_on_error:
                    self.logger.error("Stopping execution due to error (--continue-on-error not specified)")
                    self.report_logger.info("Stopping execution due to error (--continue-on-error not specified)")
                    raise
        
        # Log execution summary
        total_duration = datetime.now() - start_time
        self.logger.info("\n=== COMMAND EXECUTION SUMMARY ===")
        self.logger.info(f"Total commands: {total_commands}")
        self.logger.info(f"Successful: {successful_commands}")
        self.logger.info(f"Failed: {failed_commands}")
        self.logger.info(f"Total duration: {total_duration}")
        
        self.report_logger.info("\n=== COMMAND EXECUTION SUMMARY ===")
        self.report_logger.info(f"Total commands: {total_commands}")
        self.report_logger.info(f"Successful: {successful_commands}")
        self.report_logger.info(f"Failed: {failed_commands}")
        self.report_logger.info(f"Total duration: {total_duration}")
    
    def _execute_single_command(self, command: str) -> None:
        """Execute a single command.
        
        Args:
            command: The command to execute
        """
        command_map = {
            'prefix-dropbox-account-files': self._prefix_dropbox_account_files,
            'prefix-dropbox-account-file': self._prefix_dropbox_account_file,
            'delete-salesforce-account': self._delete_salesforce_account,
            'create-salesforce-account': self._create_salesforce_account,
            'delete-salesforce-account-file': self._delete_salesforce_account_file,
            'upload-salesforce-account-file': self._upload_salesforce_account_file,
            'upload-salesforce-account-files': self._upload_salesforce_account_files,
            'download-salesforce-account-file': self._download_salesforce_account_file,
            'delete-salesforce-account-files': self._delete_salesforce_account_files,
            'force-delete-salesforce-account-files': self._force_delete_salesforce_account_files,
            'extract-dropbox-account-app-files-dob-gender': self._extract_dropbox_account_app_files_dob_gender,
            'extract-dropbox-account-app-files-info': self._handle_extract_dropbox_account_app_files_info,
            'store-in-supabase': self._store_in_supabase,
            'search-supabase': self._search_supabase,
            'list-dropbox-account-app-files': self._list_dropbox_account_app_files
        }
        
        if command not in command_map:
            error_msg = f"Unknown command: {command}"
            self.logger.error(error_msg)
            self.report_logger.info(error_msg)
            raise ValueError(error_msg)
        
        self.logger.info(f"Executing command handler: {command}")
        command_map[command]()
    
    def _prefix_dropbox_account_files(self) -> None:
        """Prefix files in Dropbox account folder with date."""
        self.logger.info("Starting prefix-dropbox-account-files operation")
        self.report_logger.info("\n=== PREFIXING DROPBOX ACCOUNT FILES ===")
        
        # Get required context
        try:
            file_manager = self.get_context('file_manager')
            dropbox_client = self.get_context('dropbox_client')
            dropbox_root_folder = self.get_context('dropbox_root_folder')
            dropbox_account_info = self.get_data('dropbox_account_info')
            dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
            dropbox_salesforce_folder = dropbox_client.get_dropbox_salesforce_folder()
        

            self.logger.info(f"file_manager: {file_manager}")
            self.logger.info(f"dropbox_client: {dropbox_client}")
            self.logger.info(f"dropbox_account_info: {dropbox_account_info}")
            self.logger.info(f"dropbox_account_folder_name: {dropbox_account_folder_name}")
            self.logger.info(f"dropbox_salesforce_folder: {dropbox_salesforce_folder}")

            # Verify account folder exists in Dropbox
            account_folders = dropbox_client.get_dropbox_account_names()
            if dropbox_account_folder_name not in account_folders:
                error_msg = f"Account folder '{dropbox_account_folder_name}' not found in Dropbox"
                self.logger.error(error_msg)
                self.report_logger.error(f"\n{error_msg}")
                return

            # Construct source and destination paths
            source_path = f"/{dropbox_root_folder}/{dropbox_account_folder_name}"
            dest_path = f"/{dropbox_salesforce_folder}/{dropbox_account_folder_name}"

            # Clean paths for Dropbox API
            source_path = source_path.replace('//', '/')
            dest_path = dest_path.replace('//', '/')

            self.logger.info(f"Source path: {source_path}")
            self.logger.info(f"Destination path: {dest_path}")

            # Check if folder already exists in Salesforce folder
            try:
                dropbox_client.dbx.files_get_metadata(dest_path)
                # Folder exists, prompt for deletion
                self.logger.info(f"Folder already exists in Salesforce folder: {dest_path}")
                self.report_logger.info(f"\nFolder already exists in Salesforce folder: {dest_path}")
                
                # response = input(f"\nDo you want to delete the existing Dropbox folder at {dest_path}? (y/N): ").strip().lower()
                # if response != 'y':
                #     self.logger.info("Operation cancelled by user")
                #     self.report_logger.info("\nOperation cancelled by user")
                #     return
                return
                
                # Delete existing folder
                self.logger.info(f"Deleting existing folder: {dest_path}")
                self.report_logger.info(f"\nDeleting existing folder: {dest_path}")
                dropbox_client.dbx.files_delete_v2(dest_path)
                
            except dropbox.exceptions.ApiError as e:
                if not e.error.is_path() or not e.error.get_path().is_not_found():
                    # Re-raise if it's not a "not found" error
                    raise

            # Copy folder to Salesforce folder
            self.logger.info(f"Copying folder from {source_path} to {dest_path}")
            self.report_logger.info(f"\nCopying folder from {source_path} to {dest_path}")
            
            # Use the Dropbox API to copy the folder
            dropbox_client.dbx.files_copy_v2(source_path, dest_path)

            # List all files in the source folder to get original modified dates
            source_files = list_dropbox_folder_contents(dropbox_client.dbx, source_path)
            source_file_dates = {}
            for file in source_files:
                if isinstance(file, dropbox.files.FileMetadata):
                    source_file_dates[file.name] = file.server_modified

            # List all files in the copied folder
            dest_files = list_dropbox_folder_contents(dropbox_client.dbx, dest_path)
            
            # Process each file
            for file in dest_files:
                if isinstance(file, dropbox.files.FileMetadata):
                    # Check if file already has a date prefix (with or without space)
                    if len(file.name) >= 6 and file.name[:6].isdigit():
                        # Validate that the 6 digits form a valid date (YYMMDD)
                        prefix = file.name[:6]
                        year = int(prefix[:2])
                        month = int(prefix[2:4])
                        day = int(prefix[4:6])
                        
                        # Check if it's a valid date
                        try:
                            # Convert YY to YYYY (assuming 20xx for years < 50, 19xx for years >= 50)
                            full_year = 2000 + year if year < 50 else 1900 + year
                            datetime.datetime(full_year, month, day)
                            # If we get here, it's a valid date
                            self.logger.info(f"Skipping already prefixed file: {file.name}")
                            self.report_logger.info(f"\nSkipping already prefixed file: {file.name}")
                            continue
                        except ValueError:
                            # Not a valid date, continue with renaming
                            pass

                    # Get the original file's modified date
                    original_date = source_file_dates.get(file.name)
                    if original_date:
                        # Create date prefix from original file's modified date
                        date_prefix = original_date.strftime('%y%m%d')
                        
                        # Create new name with date prefix
                        new_name = f"{date_prefix} {file.name}"
                        
                        if new_name != file.name:
                            # Construct new path
                            new_path = f"{os.path.dirname(file.path_display)}/{new_name}"
                            new_path = new_path.replace('//', '/')
                            
                            # Move/rename the file
                            self.logger.info(f"Renaming file: {file.path_display} -> {new_path}")
                            self.report_logger.info(f"\nRenaming file: {file.path_display} -> {new_path}")
                            dropbox_client.dbx.files_move_v2(file.path_display, new_path)
                            
                            # Log the renamed file to the report logger
                            self.report_logger.info(f"Renamed file: {file.path_display} -> {new_path}")

            self.logger.info("Successfully completed prefix-dropbox-account-files operation")
            self.report_logger.info("\nSuccessfully completed prefix-dropbox-account-files operation")

        except Exception as e:
            error_msg = f"Error in prefix-dropbox-account-files operation: {str(e)}"
            self.logger.error(error_msg)
            self.report_logger.error(f"\n{error_msg}")
            raise
    
    def _prefix_dropbox_account_file(self) -> None:
        """Prefix a single file in Dropbox account folder with date."""
        self.logger.info("Starting prefix-dropbox-account-file operation")
        self.report_logger.info("\n=== PREFIXING SINGLE DROPBOX ACCOUNT FILE ===")
        # TODO: Implement single file prefixing logic
        self.logger.info("prefix-dropbox-account-file operation completed")
    
    def _delete_salesforce_account(self) -> None:
        """Delete an account from Salesforce."""
        self.logger.info("Starting delete-salesforce-account operation")
        self.report_logger.info("\n=== DELETING SALESFORCE ACCOUNT ===")
        # TODO: Implement account deletion logic
        self.logger.info("delete-salesforce-account operation completed")
    
    def _create_salesforce_account(self) -> None:
        """Create a new account in Salesforce."""
        self.logger.info("Starting create-salesforce-account operation")
        self.report_logger.info("\n=== CREATING SALESFORCE ACCOUNT ===")
        # TODO: Implement account creation logic
        self.logger.info("create-salesforce-account operation completed")
    
    def _delete_salesforce_account_file(self) -> None:
        """Delete a file from Salesforce account."""
        self.logger.info("Starting delete-salesforce-account-file operation")
        self.report_logger.info("\n=== DELETING SALESFORCE ACCOUNT FILE ===")
        # TODO: Implement file deletion logic
        self.logger.info("delete-salesforce-account-file operation completed")
    
    def _upload_salesforce_account_file(self) -> None:
        """Upload a single file to Salesforce account."""
        self.logger.info("Starting upload-salesforce-account-file operation")
        self.report_logger.info("\n=== UPLOADING SINGLE FILE TO SALESFORCE ===")
        # TODO: Implement single file upload logic
        self.logger.info("upload-salesforce-account-file operation completed")
    
    def _upload_salesforce_account_files(self) -> None:
        """Upload all files from Dropbox account to Salesforce."""
        self.logger.info("Starting upload-salesforce-account-files operation")
        self.report_logger.info("\n=== UPLOADING FILES TO SALESFORCE ===")
        
        try:
            # Get required context
            browser = self.get_context('browser')
            page = self.get_context('page')
            dropbox_client = self.get_context('dropbox_client')
            dropbox_root_folder = self.get_context('dropbox_root_folder')
            dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
            dropbox_salesforce_folder = dropbox_client.get_dropbox_salesforce_folder()
            file_manager = self.get_context('file_manager')
            account_manager = self.get_context('account_manager')

            # Construct source path
            source_path = f"/{dropbox_salesforce_folder}/{dropbox_account_folder_name}"
            
            # Clean paths for Dropbox API
            source_path = source_path.replace('//', '/')
            
            self.logger.info(f"Source path: {source_path}")
            
            # Check if source folder exists
            try:
                dropbox_client.dbx.files_get_metadata(source_path)
            except dropbox.exceptions.ApiError as e:
                if e.error.is_path() and e.error.get_path().is_not_found():
                    error_msg = f"Source folder not found: {source_path}"
                    self.logger.error(error_msg)
                    self.report_logger.error(f"\n{error_msg}")
                    return
                raise
            
            # List all files in source folder
            files = list_dropbox_folder_contents(dropbox_client.dbx, source_path)
            
            if not files:
                self.logger.info("No files found to upload to Salesforce")
                self.report_logger.info("\nNo files found to upload to Salesforce")
                return
            
            # Create a temporary directory for downloads
            temp_dir = os.path.join(os.getcwd(), 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # Download and upload each file
                self.logger.info(f"Download and upload {len(files)} files")
                for file in files:
                    if isinstance(file, dropbox.files.FileMetadata):
                        self.logger.info(f"Processing file: {file.name}")
                        self.report_logger.info(f"\nProcessing file: {file.name}")
                        
                        # Download file from Dropbox
                        logging.info(f"Downloading file: {file.name}")
                        local_path = os.path.join(temp_dir, file.name)
                        self.logger.info(f"Downloading to: {local_path}")
                        dropbox_client.dbx.files_download_to_file(local_path, file.path_display)
                        
                        account_manager.navigate_back_to_account_page()

                        # Navigate to files section
                        logging.info("Navigating to files section")
                        num_files = file_manager.navigate_to_account_files_click_on_files_card_to_facilitate_file_operation()
                        if num_files == -1:
                            logging.error("Failed to navigate to Files")
                            return

                        # Check if file already exists in Salesforce
                        file_name = os.path.splitext(file.name)[0]  # Remove extension for comparison
                        logging.info(f'checking if file {file_name} exists in salesforce')
                        if file_manager.search_salesforce_file(file_name):
                            self.logger.info(f"File {file_name} already exists in Salesforce, skipping upload")
                            self.report_logger.info(f"\nFile {file_name} already exists in Salesforce, skipping upload")
                            # Clean up the downloaded file since we won't be using it
                            os.remove(local_path)
                            self.logger.info(f"Cleaned up temporary file: {local_path}")
                            continue
        
                        # Upload file to Salesforce via browser with retries
                        self.logger.info(f"Uploading to Salesforce: {file.name}")
                        self.logger.info(f"Uploading file: {local_path}")
                        self.logger.info("current url: {page.url}")
                        if not upload_account_file_with_retries(page, local_path, expected_items=num_files+1):
                            logging.error(f"Failed to upload file after all retries: {local_path}")
                            if not self.args.continue_on_error:
                                raise Exception(f"Failed to upload file: {local_path}")
                        
                        # Clean up the downloaded file
                        os.remove(local_path)
                        self.logger.info(f"Cleaned up temporary file: {local_path}")
                
            except Exception as e:
                self.logger.error(f"Error processing files: {str(e)}")
                raise
            finally:
                # Clean up temporary directory
                try:
                    os.rmdir(temp_dir)
                    self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    self.logger.warning(f"Could not remove temporary directory {temp_dir}: {str(e)}")
            
            self.logger.info("Successfully completed upload-salesforce-account-files operation")
            self.report_logger.info("\nSuccessfully completed upload-salesforce-account-files operation")
            
        except Exception as e:
            error_msg = f"Error in upload-salesforce-account-files operation: {str(e)}"
            self.logger.error(error_msg)
            self.report_logger.error(f"\n{error_msg}")
            raise
    
    def _download_salesforce_account_file(self) -> None:
        """Download a file from Salesforce account."""
        self.logger.info("Starting download-salesforce-account-file operation")
        self.report_logger.info("\n=== DOWNLOADING FILE FROM SALESFORCE ===")
        # TODO: Implement file download logic
        self.logger.info("download-salesforce-account-file operation completed")
    
    def _delete_salesforce_account_files(self, force: bool = False) -> None:
        """Delete all files from Salesforce account.
        
        Args:
            force: If True, skip the confirmation prompt
        """
        self.logger.info("Starting delete-salesforce-account-files operation")
        self.report_logger.info("\n=== DELETING SALESFORCE ACCOUNT FILES ===")
        
        try:
            # Get required context
            salesforce_account_id = self.get_data('salesforce_account_id')
            salesforce_acount_file_names = self.get_data('salesforce_acount_file_names')
            file_manager = self.get_context('file_manager')
            
            if not salesforce_account_id:
                error_msg = "No Salesforce account ID found"
                self.logger.error(error_msg)
                self.report_logger.error(f"\n{error_msg}")
                return
            
            self.logger.info(f"Salesforce account ID: {salesforce_account_id}")
            
            # Get all files associated with the account
            files = salesforce_acount_file_names
            
            if not files:
                self.logger.info("No files found to delete")
                self.report_logger.info("\nNo files found to delete")
                return
            
            # Prompt for confirmation unless force is True
            self.logger.info(f"Found {len(files)} files to delete")
            self.report_logger.info(f"\nFound {len(files)} files to delete:")
            for file in files:
                self.report_logger.info(f"  - {file}")
            
            if not force:
                response = input(f"\nDo you want to delete all {len(files)} Salesforce account files? (y/N): ").strip().lower()
                if response != 'y':
                    self.logger.info("Operation cancelled by user")
                    self.report_logger.info("\nOperation cancelled by user")
                    return
            
            # Delete each file
            for file in files:
                try:
                    self.logger.info(f"Deleting file: {file}")
                    self.report_logger.info(f"\nDeleting file: {file}")
                    logging.info(f"Attempting to delete first file: {file}")
        
                    if not file_manager.delete_salesforce_file(file):
                        logging.error(f"Failed to delete file: {file}")
                        return
                except Exception as e:
                    error_msg = f"Error deleting file {file}: {str(e)}"
                    self.logger.error(error_msg)
                    self.report_logger.error(f"\n{error_msg}")
                    if not self.args.continue_on_error:
                        raise
            
            self.logger.info("Successfully completed delete-salesforce-account-files operation")
            self.report_logger.info("\nSuccessfully completed delete-salesforce-account-files operation")
            
        except Exception as e:
            error_msg = f"Error in delete-salesforce-account-files operation: {str(e)}"
            self.logger.error(error_msg)
            self.report_logger.error(f"\n{error_msg}")
            raise

    def _force_delete_salesforce_account_files(self) -> None:
        """Force delete all files from Salesforce account without confirmation prompt."""
        self.logger.info("Starting force-delete-salesforce-account-files operation")
        self.report_logger.info("\n=== FORCE DELETING SALESFORCE ACCOUNT FILES ===")
        self._delete_salesforce_account_files(force=True)

    def _extract_dropbox_account_app_files_dob_gender(self) -> None:
        """Get Dropbox Account information from all the application files in each Dropbox account folder.
           Currently only gets the DOB and gender from the application files.
        """
        self.logger.info("Starting extract-dropbox-account-app-files-dob-gender operation")
        self.report_logger.info("\n=== GETTING DROPBOX APPLICATION INFORMATION ===")
        
        try:
            # Get required context
            dropbox_client = self.get_context('dropbox_client')
            dropbox_root_folder = self.get_context('dropbox_root_folder')
            dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
            logging.info(f"dropbox_account_folder_name: {dropbox_account_folder_name}")

            # Construct folder path
            folder_path = f"/{dropbox_root_folder}/{dropbox_account_folder_name}"
            folder_path = folder_path.replace('//', '/')
            
            # Extract only birthdate and gender information
            summary_data = dropbox_client.extract_app_files_info(folder_path, extract_fields={'birthdate', 'gender'})
            
            # Log the summary for this folder
            folder_app_files = summary_data['all_folder_app_files'].get(folder_path, [])
            files_with_birthdate_in_folder = [file for file in folder_app_files if file.path_display in summary_data['files_with_birthdate']]
            
            self.summary_logger.info(f"\nDropbox Account Folder: {dropbox_account_folder_name}")
            if files_with_birthdate_in_folder:
                for file in files_with_birthdate_in_folder:
                    birthdate = summary_data['file_birthdates'].get(file.path_display, '')
                    sex = summary_data['file_sexes'].get(file.path_display, '')
                    if sex:
                        if sex.upper().startswith('F'):
                            sex_icon = '👩'
                        elif sex.upper().startswith('M'):
                            sex_icon = '👨'
                        else:
                            sex_icon = ''
                        sex_str = f", ☑️ {sex_icon} {sex}"
                    else:
                        sex_str = ", ❌ F/M"
                    self.summary_logger.info(f"  ✅🎂 {file.name} [{birthdate}{sex_str}]")
            else:
                self.summary_logger.info(f"  ❌ No application files found for {dropbox_account_folder_name}")

            self.logger.info("\nSuccessfully completed extract-dropbox-account-app-files-dob-gender operation")
            
        except Exception as e:
            error_msg = f"Error in extract-dropbox-account-app-files-dob-gender operation: {str(e)}"
            self.logger.error(error_msg)
            raise

    def _handle_extract_dropbox_account_app_files_info(self) -> None:
        """Handle the extract-dropbox-account-app-files-info command."""
        self.logger.info("Executing command handler: extract-dropbox-account-app-files-info")
        self.logger.info("Starting extract-dropbox-account-app-files-info operation")
        
        # Get the folder name and file filter from data and args
        dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
        file_filter = self.args.file_filter
        
        # Call the implementation method with required arguments
        self._extract_dropbox_account_app_files_info(dropbox_account_folder_name, file_filter)

    def _extract_dropbox_account_app_files_info(self, dropbox_account_folder_name: str, file_filter: Optional[str] = None) -> None:
        """Extract information from application files in the specified Dropbox account folder."""
        start_time = time.time()
        self.logger.info("\n=== GETTING DROPBOX APPLICATION INFORMATION ===")
        self.logger.info(f"dropbox_account_folder_name: {dropbox_account_folder_name}")
        self.logger.info(f"dropbox_account_name_parts: {self._data.get('dropbox_account_name_parts')}")
        
        if file_filter:
            self.logger.info(f"Using file filter: {file_filter} (only files matching this pattern will be processed)")
            self.logger.info(f"\nUsing file filter: {file_filter} (only files matching this pattern will be processed)")
        
        try:
            # Get Dropbox client and folder names from context
            dropbox_client = self._context.get('dropbox_client')
            dropbox_root_folder = self._context.get('dropbox_root_folder')
            if not dropbox_client:
                raise ValueError("Dropbox client not found in context")
            
            # Construct folder path
            folder_path = f"{dropbox_root_folder}/{dropbox_account_folder_name}"
            folder_path = folder_path.replace('//', '/')
            
            # Get list of files in the folder
            list_start = time.time()
            from sync.dropbox_client.utils.dropbox_utils import list_dropbox_folder_contents
            files = list_dropbox_folder_contents(dropbox_client.dbx, folder_path)
            files = [f for f in files if isinstance(f, dropbox.files.FileMetadata)]
            list_time = time.time() - list_start
            self.logger.info(f"Time to list files: {list_time:.2f} seconds")
            
            # Filter files if file_filter is provided
            if file_filter:
                files = [f for f in files if fnmatch.fnmatch(f.name, file_filter)]
                self.logger.info(f"\nFound {len(files)} files matching filter '{file_filter}' in {folder_path}:")
                for file in files:
                    self.logger.info(f"  ✅ {file.name}")
            
            # Extract all fields except birthdate and gender
            extract_start = time.time()
            summary_data = dropbox_client.extract_app_files_info(
                folder_path, 
                extract_fields={'name', 'address'}, 
                file_filter=file_filter
            )
            extract_time = time.time() - extract_start
            self.logger.info(f"Time to extract information: {extract_time:.2f} seconds")
            
            # Log the extracted information
            if summary_data and 'file_info' in summary_data:
                filter_text = f" matching File Filter: {file_filter}" if file_filter else ""
                self.summary_logger.info(f"\nDropbox Account Application File Information for Folder{filter_text}: {dropbox_account_folder_name}")
                for file in files:
                    if file.path_display in summary_data['file_info']:
                        info = summary_data['file_info'][file.path_display]
                        self.summary_logger.info(f"  ✅ {file.name}")
                        log_dropbox_app_file_info(info, self.summary_logger)
            else:
                if file_filter:
                    self.summary_logger.info(f"  ❌ No application files found matching filter '{file_filter}' for {dropbox_account_folder_name}")
                else:
                    self.summary_logger.info(f"  ❌ No application files found for {dropbox_account_folder_name}")
            
            # Log timing information
            total_time = time.time() - start_time
            self.logger.info("\n=== TIMING INFORMATION ===")
            self.logger.info(f"Total processing time: {total_time:.2f} seconds")
            self.logger.info(f"Time to list files: {list_time:.2f} seconds")
            self.logger.info(f"Time to extract information: {extract_time:.2f} seconds")
            
            # Log detailed timing information from the extractor if available
            if summary_data and 'timing_info' in summary_data:
                self.logger.info("\nDetailed timing information from extractor:")
                for operation, duration in summary_data['timing_info']['operations'].items():
                    self.logger.info(f"{operation}: {duration:.2f} seconds")
            
            self.logger.info("\nSuccessfully completed extract-dropbox-account-app-files-info operation")
            
        except Exception as e:
            self.logger.error(f"Error extracting app files info: {str(e)}")
            raise

    def _store_in_supabase(self) -> None:
        """Store data in Supabase database.
        This command will store the extracted DOB and gender information in Supabase.
        """
        self.logger.info("Starting store-in-supabase operation")
        self.report_logger.info("\n=== STORING DATA IN SUPABASE ===")
        
        # Get required context
        dropbox_client = self.get_context('dropbox_client')
        dropbox_salesforce_folder = dropbox_client.get_dropbox_salesforce_folder()
        dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
        logging.info(f"dropbox_account_folder_name: {dropbox_account_folder_name}")

        try:
            # Get or create Supabase client
            try:
                supabase_client = self.get_context('supabase_client')
                self.logger.info("Using existing Supabase client from context")
            except KeyError:
                self.logger.info("No Supabase client found in context, creating new instance")
                from supabase_client import SupabaseClient
                supabase_client = SupabaseClient()
                self.set_context('supabase_client', supabase_client)
            
            # Get the dropbox account folder from the database
            self.logger.info(f"Getting dropbox account from database for {dropbox_account_folder_name}")
            dropbox_account = supabase_client.get_dropbox_account_by_folder(dropbox_account_folder_name)
            if not dropbox_account:
                error_msg = f"Dropbox account not found for folder: {dropbox_account_folder_name}"
                self.logger.error(error_msg)
                self.report_logger.error(f"\n{error_msg}")
                return

            # Get the applications for the dropbox account
            applications = dropbox_account.applications
            self.logger.info(f"Found {len(applications)} applications for {dropbox_account_folder_name}")
            self.report_logger.info(f"\nFound {len(applications)} applications for {dropbox_account_folder_name}")

            # Generate the current account summary
            account_summary = supabase_client.generate_account_summary(dropbox_account_folder_name)
            self.logger.info(f"Account summary for {dropbox_account_folder_name}:\n{account_summary}")
            self.report_logger.info(f"\nAccount summary for {dropbox_account_folder_name}:\n{account_summary}")

            # Store the applications in Supabase
            for application in applications:
                supabase_client.store_application(application)
            
            # Get the data to store
            summary_data = self.get_data('summary_data')
            if not summary_data:
                error_msg = "No summary data found to store in Supabase"
                self.logger.error(error_msg)
                self.report_logger.error(f"\n{error_msg}")
                return
            
            # Store the data in Supabase
            for folder, files in summary_data['all_folder_app_files'].items():
                for file in files:
                    if file.path_display in summary_data['files_with_birthdate']:
                        birthdate = summary_data['file_birthdates'].get(file.path_display, '')
                        sex = summary_data['file_sexes'].get(file.path_display, '')
                        
                        # Prepare data for Supabase
                        data = {
                            'folder_name': folder,
                            'file_name': file.name,
                            'file_path': file.path_display,
                            'birthdate': birthdate,
                            'sex': sex,
                            'created_at': datetime.now().isoformat()
                        }
                        
                        try:
                            # Update data into Supabase using the client        
                            result = supabase_client.client.table('account_files').update(data).eq('file_path', file.path_display).execute()
                            self.logger.info(f"Successfully stored data for {file.name} in Supabase")
                            self.report_logger.info(f"\nSuccessfully stored data for {file.name} in Supabase")
                        except Exception as e:
                            error_msg = f"Error storing data for {file.name} in Supabase: {str(e)}"
                            self.logger.error(error_msg)
                            self.report_logger.error(f"\n{error_msg}")
                            if not self.args.continue_on_error:
                                raise
            
            self.logger.info("Successfully completed store-in-supabase operation")
            self.report_logger.info("\nSuccessfully completed store-in-supabase operation")
            
        except Exception as e:
            error_msg = f"Error in store-in-supabase operation: {str(e)}"
            self.logger.error(error_msg)
            self.report_logger.error(f"\n{error_msg}")
            raise

    def _search_supabase(self) -> None:
        """Search for account information in Supabase database.
        This command will search for account information in Supabase based on various criteria.
        """
        self.logger.info("Starting search-supabase operation")
        self.report_logger.info("\n=== SEARCHING SUPABASE DATABASE ===")
        
        try:
            # Get or create Supabase client
            try:
                supabase_client = self.get_context('supabase_client')
                self.logger.info("Using existing Supabase client from context")
            except KeyError:
                self.logger.info("No Supabase client found in context, creating new instance")
                from supabase_client.client import SupabaseClient
                supabase_client = SupabaseClient()
                self.set_context('supabase_client', supabase_client)
            
            # Get search criteria from data
            self.logger.debug("Available data keys: %s", list(self._data.keys()))
            folder_name = self.get_data('dropbox_account_folder_name')
            if not folder_name:
                self.logger.error("No search criteria provided. Please provide a folder name.")
                return
            
            # Get additional search criteria if provided
            search_criteria = {}
            try:
                if self.get_data('birthdate'):
                    search_criteria['birthdate'] = self.get_data('birthdate')
            except KeyError:
                pass
                
            try:
                if self.get_data('gender'):
                    search_criteria['gender'] = self.get_data('gender')
            except KeyError:
                pass
                
            try:
                if self.get_data('application_type'):
                    search_criteria['application_type'] = self.get_data('application_type')
            except KeyError:
                pass
            
            # Search in Supabase
            self.logger.info("Searching for account: %s", folder_name)
            result = supabase_client.generate_search_results_summary(folder_name, search_criteria)
            self.report_logger.info(result)
            
        except Exception as e:
            import traceback
            error_msg = f"Error searching Supabase: {str(e)}"
            stack_trace = traceback.format_exc()
            self.logger.error(error_msg)
            self.logger.error("Stack trace:\n%s", stack_trace)
            self.report_logger.error(f"\n{error_msg}")
            self.report_logger.error(f"\nStack trace:\n{stack_trace}") 

    def _list_dropbox_account_app_files(self) -> None:
        """List all application files in the Dropbox account folder.
        This command will list all files that appear to be application files in the specified Dropbox account folder.
        """
        self.logger.info("Starting list-dropbox-account-app-files operation")
        self.report_logger.info("\n=== LISTING DROPBOX ACCOUNT APPLICATION FILES ===")
        
        try:
            # Get required context
            dropbox_client = self.get_context('dropbox_client')
            dropbox_root_folder = self.get_context('dropbox_root_folder')
            dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
            logging.info(f"dropbox_account_folder_name: {dropbox_account_folder_name}")

            # Get file filter if specified
            file_filter = self.args.file_filter
            if file_filter:
                self.logger.info(f"Using file filter: {file_filter} (only files matching this pattern will be listed)")
                self.report_logger.info(f"\nUsing file filter: {file_filter} (only files matching this pattern will be listed)")

            # Construct folder path
            folder_path = f"/{dropbox_root_folder}/{dropbox_account_folder_name}"
            folder_path = folder_path.replace('//', '/')
            
            # List all files in the folder
            files = list_dropbox_folder_contents(dropbox_client.dbx, folder_path)
            
            # Filter for application files
            app_files = []
            for file in files:
                if isinstance(file, dropbox.files.FileMetadata):
                    # Check if file matches filter if specified
                    if file_filter and not fnmatch.fnmatch(file.name.lower(), file_filter.lower()):
                        continue
                    
                    # Check if file appears to be an application file
                    if any(keyword in file.name.lower() for keyword in ['application', 'app', 'form', 'registration']):
                        app_files.append(file)
            
            # Log the results
            self.summary_logger.info(f"\nDropbox Account Folder: {dropbox_account_folder_name}")
            if app_files:
                self.summary_logger.info(f"Found {len(app_files)} application files:")
                for file in app_files:
                    self.summary_logger.info(f"  📄 {file.name}")
                    # Log file metadata
                    self.summary_logger.info(f"    📅 Modified: {file.server_modified}")
                    self.summary_logger.info(f"    📦 Size: {file.size:,} bytes")
            else:
                self.summary_logger.info(f"  ❌ No application files found for {dropbox_account_folder_name}")

            self.logger.info("\nSuccessfully completed list-dropbox-account-app-files operation")
            
        except Exception as e:
            error_msg = f"Error in list-dropbox-account-app-files operation: {str(e)}"
            self.logger.error(error_msg)
            raise 