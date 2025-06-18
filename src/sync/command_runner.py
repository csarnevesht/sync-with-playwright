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
from sync.dropbox_client.utils.logging_utils import log_dropbox_app_file_info, log_best_dropbox_account_app_info, log_app_files_notes_summary, log_app_files_processing_summary
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
        # Check if this command should be skipped for the current account
        dropbox_account_name = getattr(self.args, 'dropbox_account_name', None)
        if dropbox_account_name:
            from sync.utils.name_utils import should_skip_command_for_account
            if should_skip_command_for_account(dropbox_account_name, command):
                self.logger.info(f"Skipping command '{command}' for account '{dropbox_account_name}' due to special case rule")
                self.report_logger.info(f"Skipping command '{command}' for account '{dropbox_account_name}' due to special case rule")
                return
        
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

    def _handle_extract_dropbox_account_app_files_info(self) -> None:
        """Handle the extract-dropbox-account-app-files-info command."""
        self.logger.info("Executing command handler: extract-dropbox-account-app-files-info")
        self.logger.info("Starting extract-dropbox-account-app-files-info operation")
        
        # Get the folder name and file filter from data and args
        dropbox_account_folder_name = self.get_data('dropbox_account_folder_name')
        file_filter = self.args.file_filter
        
        # Call the implementation method with required arguments
        self._extract_dropbox_account_app_files_info(dropbox_account_folder_name, file_filter)

    def _has_complete_account_info(self, dropbox_account_search_result: Dict[str, Any]) -> bool:
        """Check if the dropbox account search result has complete account info including birthdate and gender.
        
        Args:
            dropbox_account_search_result: Dictionary containing account search result
            
        Returns:
            bool: True if complete account info is present (including birthdate and gender), False otherwise
        """
        account_data = dropbox_account_search_result.get('account_data', {})
        
        # Required fields for complete account info (email is optional)
        required_fields = {
            'name', 'first_name', 'last_name', 'address', 'city', 'state', 'zip', 'phone', 'birthdate', 'gender'
        }
        
        # Check if all required fields are present and not empty
        for field in required_fields:
            value = account_data.get(field, '')
            if not value or str(value).strip() == '' or str(value).lower() in ['nan', 'none', 'null']:
                return False
        
        # Check if we have a match found
        search_info = dropbox_account_search_result.get('search_info', {})
        match_info = search_info.get('match_info', {})
        match_status = match_info.get('match_status', '')
        
        # Only consider it complete if we found a match
        if 'match found' not in match_status.lower():
            return False
        
        return True

    def _extract_dropbox_account_app_files_info(self, dropbox_account_folder_name: str, file_filter: Optional[str] = None) -> None:
        """Extract information from application files in the specified Dropbox account folder."""
        start_time = time.time()
        self.logger.info("\n=== GETTING DROPBOX APPLICATION INFORMATION ===")
        self.logger.info(f"dropbox_account_folder_name: {dropbox_account_folder_name}")
        self.logger.info(f"dropbox_account_name_parts: {self._data.get('dropbox_account_name_parts')}")
        
        # Check if we already have complete account info from dropbox search
        dropbox_account_search_result = self.get_data('dropbox_account_info')
        if dropbox_account_search_result and self._has_complete_account_info(dropbox_account_search_result):
            self.logger.info("✅ Account already has complete information from Dropbox search - skipping app files extraction")
            self.report_logger.info("✅ Account already has complete information from Dropbox search - skipping app files extraction")
            self.summary_logger.info(f"✅ Skipped app files extraction for {dropbox_account_folder_name} - complete account info already available")
            return
        
        if file_filter:
            self.logger.info(f"Using file filter: {file_filter} (only files matching this pattern will be processed)")
            self.logger.info(f"\nUsing file filter: {file_filter} (only files matching this pattern will be processed)")
        
        try:
            # Get Dropbox client and folder names from context
            dropbox_client = self.get_context('dropbox_client')
            dropbox_root_folder = self.get_context('dropbox_root_folder')
            
            # Construct folder path
            folder_path = f"/{dropbox_root_folder}/{dropbox_account_folder_name}"
            folder_path = folder_path.replace('//', '/')
            
            # First pass: Extract all fields except birthdate and gender, skipping 0-length files
            extract_start = time.time()
            
            # Always skip zero-length files during initial processing
            summary_data = dropbox_client.extract_app_files_info(
                folder_path, 
                extract_fields={'name', 'address'}, 
                file_filter=file_filter,
                skip_zero_length_if_account_info_exists=True,  # Always skip 0-length files initially
                report_logger=self.report_logger
            )
            extract_time = time.time() - extract_start
            self.logger.info(f"Extraction completed in {extract_time:.2f} seconds")
            
            # Log if we skipped any zero-length files
            if summary_data and 'skipped_zero_length_files' in summary_data and summary_data['skipped_zero_length_files'] > 0:
                self.logger.info(f"Skipped {summary_data['skipped_zero_length_files']} zero-length files during initial processing")
                self.report_logger.info(f"Skipped {summary_data['skipped_zero_length_files']} zero-length files during initial processing")
            
            # Store the aggregated account info from app files
            if summary_data:
                # Get the list of files that were processed
                # The app file extractor returns files in all_folder_app_files
                folder_path_key = folder_path
                files = summary_data.get('all_folder_app_files', {}).get(folder_path_key, [])
                
                # Aggregate the account info
                aggregated_info = self._aggregate_account_info_from_app_files(summary_data, files)
                
                # Store the aggregated info
                self.set_data('account_info_from_app_files', aggregated_info)
                
                # Log the results
                self.logger.info(f"✅ Successfully extracted information from {len(files)} application files")
                self.logger.info(f"Files with complete info: {aggregated_info.get('files_with_complete_info', 0)}")
                self.logger.info(f"Files with partial info: {aggregated_info.get('files_with_partial_info', 0)}")
                self.logger.info(f"Files with no info: {aggregated_info.get('files_with_no_info', 0)}")
                
                # Log the best dropbox account app files info
                best_info = aggregated_info.get('best_available_info', {})
                log_best_dropbox_account_app_info(
                    best_info, 
                    self.summary_logger, 
                    self.report_logger, 
                    "BEST ACCOUNT APP FILES INFO"
                )
                
                # Log detailed notes for each app file
                if summary_data and 'file_info' in summary_data:
                    log_app_files_processing_summary(
                        summary_data,
                        self.summary_logger,
                        self.report_logger
                    )
                
                # Check if we have complete account info from app files
                has_complete_account_info = aggregated_info.get('has_complete_account_info', False)
                
                if has_complete_account_info:
                    self.logger.info("✅ Complete account information found from app files")
                    self.report_logger.info("✅ Complete account information found from app files")
                else:
                    self.logger.info("⚠️ Incomplete account information from app files")
                    self.report_logger.info("⚠️ Incomplete account information from app files")
                    
                    # If we don't have complete account info, process the 0-length files
                    if summary_data and 'skipped_zero_length_files' in summary_data and summary_data['skipped_zero_length_files'] > 0:
                        self.logger.info(f"Processing {summary_data['skipped_zero_length_files']} zero-length files to try to get complete account info")
                        self.report_logger.info(f"Processing {summary_data['skipped_zero_length_files']} zero-length files to try to get complete account info")
                        
                        # Second pass: Process 0-length files to try to get complete account info
                        zero_length_summary = dropbox_client.extract_app_files_info(
                            folder_path, 
                            extract_fields={'name', 'address'}, 
                            file_filter=file_filter,
                            skip_zero_length_if_account_info_exists=False,  # Process 0-length files
                            report_logger=self.report_logger
                        )
                        
                        if zero_length_summary:
                            # Get the additional files that were processed
                            additional_files = zero_length_summary.get('files', [])
                            
                            # Combine the results
                            combined_files = files + additional_files
                            combined_summary = {
                                'files': combined_files,
                                'extracted_info': summary_data.get('extracted_info', []) + zero_length_summary.get('extracted_info', []),
                                'total_files_processed': len(combined_files),
                                'skipped_zero_length_files': 0  # All files processed now
                            }
                            
                            # Re-aggregate with all files
                            updated_aggregated_info = self._aggregate_account_info_from_app_files(combined_summary, combined_files)
                            
                            # Update the stored info
                            self.set_data('account_info_from_app_files', updated_aggregated_info)
                            
                            # Log the updated results
                            self.logger.info(f"✅ After processing zero-length files: {len(combined_files)} total files processed")
                            self.logger.info(f"Files with complete info: {updated_aggregated_info.get('files_with_complete_info', 0)}")
                            self.logger.info(f"Files with partial info: {updated_aggregated_info.get('files_with_partial_info', 0)}")
                            self.logger.info(f"Files with no info: {updated_aggregated_info.get('files_with_no_info', 0)}")
                            
                            if updated_aggregated_info.get('has_complete_account_info', False):
                                self.logger.info("✅ Complete account information now found after processing zero-length files")
                                self.report_logger.info("✅ Complete account information now found after processing zero-length files")
                            else:
                                self.logger.info("⚠️ Still incomplete account information after processing zero-length files")
                                self.report_logger.info("⚠️ Still incomplete account information after processing zero-length files")
                
                # Store the summary data for reporting
                self.set_data('app_files_extraction_summary', summary_data)
                
            else:
                self.logger.warning("❌ No summary data returned from app files extraction")
                self.report_logger.warning("❌ No summary data returned from app files extraction")
                
        except Exception as e:
            self.logger.error(f"❌ Error extracting app files info: {str(e)}")
            self.report_logger.error(f"❌ Error extracting app files info: {str(e)}")
            raise
        
        total_time = time.time() - start_time
        self.logger.info(f"=== APP FILES EXTRACTION COMPLETED IN {total_time:.2f} SECONDS ===")
        self.report_logger.info(f"=== APP FILES EXTRACTION COMPLETED IN {total_time:.2f} SECONDS ===")

    def _aggregate_account_info_from_app_files(self, summary_data: Dict[str, Any], files: List[dropbox.files.FileMetadata]) -> Dict[str, Any]:
        """Aggregate account information from multiple app files into a single structure.
        
        Args:
            summary_data: The summary data from app file extraction
            files: List of files that were processed
            
        Returns:
            Dict containing aggregated account information
        """
        aggregated_info = {
            'total_files_processed': len(files),
            'files_with_complete_info': 0,
            'files_with_partial_info': 0,
            'files_with_no_info': 0,
            'best_available_info': {},
            'file_details': {},
            'has_complete_account_info': False
        }
        
        if not summary_data or 'file_info' not in summary_data:
            aggregated_info['files_with_no_info'] = len(files)
            return aggregated_info
        
        file_info = summary_data['file_info']
        best_info = {}
        best_completeness_score = 0
        
        # Process each file that was actually processed (not skipped)
        for file in files:
            file_path = file.path_display
            info = file_info.get(file_path, {})
            
            # Store file details
            aggregated_info['file_details'][file.name] = {
                'path': file_path,
                'info': info,
                'completeness_score': 0
            }
            
            if not info:
                aggregated_info['files_with_no_info'] += 1
                continue
            
            # Calculate completeness score for this file
            completeness_score = self._calculate_info_completeness(info)
            aggregated_info['file_details'][file.name]['completeness_score'] = completeness_score
            
            # Categorize file based on completeness
            if completeness_score >= 0.8:  # 80% or more complete
                aggregated_info['files_with_complete_info'] += 1
            elif completeness_score >= 0.3:  # 30% or more complete
                aggregated_info['files_with_partial_info'] += 1
            else:
                aggregated_info['files_with_no_info'] += 1
            
            # Update best available info if this file has better completeness
            if completeness_score > best_completeness_score:
                best_completeness_score = completeness_score
                best_info = info.copy()
        
        # Structure the best available info as proper account information
        if best_info:
            # Create structured account info with Owner and Joint Owner data
            account_info = {
                'owner': {},
                'jointOwner': {},
                'application_type': best_info.get('application_type', 'Unknown'),
                'status': best_info.get('status', 'Unknown'),
                'notes': best_info.get('notes', [])
            }
            
            # Add owner information if available
            if best_info.get('owner'):
                owner_data = best_info['owner']
                account_info['owner'] = {
                    'firstName': owner_data.get('firstName'),
                    'lastName': owner_data.get('lastName'),
                    'dateOfBirth': owner_data.get('dateOfBirth'),
                    'gender': owner_data.get('gender'),
                    'mailingAddressStreet': owner_data.get('mailingAddressStreet'),
                    'mailingAddressCity': owner_data.get('mailingAddressCity'),
                    'mailingAddressState': owner_data.get('mailingAddressState'),
                    'mailingAddressZip': owner_data.get('mailingAddressZip'),
                    'phoneNumber': owner_data.get('phoneNumber'),
                    'emailAddress': owner_data.get('emailAddress')
                }
                
                # Add OCR method if it was used
                if owner_data.get('ocrMethod'):
                    account_info['owner']['ocrMethod'] = owner_data['ocrMethod']
            
            # Add joint owner information if available
            if best_info.get('jointOwner'):
                joint_owner_data = best_info['jointOwner']
                account_info['jointOwner'] = {
                    'firstName': joint_owner_data.get('firstName'),
                    'lastName': joint_owner_data.get('lastName'),
                    'dateOfBirth': joint_owner_data.get('dateOfBirth'),
                    'gender': joint_owner_data.get('gender'),
                    'mailingAddressStreet': joint_owner_data.get('mailingAddressStreet'),
                    'mailingAddressCity': joint_owner_data.get('mailingAddressCity'),
                    'mailingAddressState': joint_owner_data.get('mailingAddressState'),
                    'mailingAddressZip': joint_owner_data.get('mailingAddressZip'),
                    'phoneNumber': joint_owner_data.get('phoneNumber'),
                    'emailAddress': joint_owner_data.get('emailAddress')
                }
                
                # Add OCR method if it was used
                if joint_owner_data.get('ocrMethod'):
                    account_info['jointOwner']['ocrMethod'] = joint_owner_data['ocrMethod']
            
            aggregated_info['best_available_info'] = account_info
        else:
            aggregated_info['best_available_info'] = {}
        
        # Determine if we have complete account info
        if best_completeness_score >= 0.8:
            aggregated_info['has_complete_account_info'] = True
        
        return aggregated_info

    def _calculate_info_completeness(self, info: Dict[str, Any]) -> float:
        """Calculate how complete the account information is (0.0 to 1.0).
        
        Args:
            info: File information dictionary
            
        Returns:
            Float between 0.0 and 1.0 representing completeness
        """
        if not info:
            return 0.0
        
        # Define required fields for complete account info
        required_fields = {
            'owner': ['firstName', 'lastName', 'dateOfBirth', 'gender', 'mailingAddressStreet', 'mailingAddressCity', 'mailingAddressState', 'mailingAddressZip', 'phoneNumber'],
            'jointOwner': ['firstName', 'lastName', 'dateOfBirth', 'gender']  # Joint owner is optional
        }
        
        total_fields = 0
        filled_fields = 0
        
        # Check owner fields
        owner = info.get('owner', {})
        for field in required_fields['owner']:
            total_fields += 1
            if owner.get(field) and str(owner.get(field)).strip() not in ['', 'None', 'null', 'nan']:
                filled_fields += 1
        
        # Check joint owner fields (optional, but if present should be complete)
        joint_owner = info.get('jointOwner', {})
        if joint_owner:
            for field in required_fields['jointOwner']:
                total_fields += 1
                if joint_owner.get(field) and str(joint_owner.get(field)).strip() not in ['', 'None', 'null', 'nan']:
                    filled_fields += 1
        
        # Calculate completeness score
        if total_fields == 0:
            return 0.0
        
        return filled_fields / total_fields

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