import os
from typing import Optional, List, Dict, Any
from supabase import create_client, Client as SupabaseBaseClient
from .schema import (
    ApplicationStatus, ApplicationType, DropboxAccountApplicationFile, DropboxAccountApplicationInfo,
    DropboxAccountWithFiles, DropboxAccountClientListInfo, DropboxAccountBestInfo, DropboxSalesforceMapping, 
    SyncStatus, AccountAnalysis, SalesforceAccount, SalesforceHousehold, SalesforceHouseholdMember
)
from dotenv import load_dotenv
import logging
import jwt
import time
import collections.abc
from datetime import datetime, date
import httpx
import json

logger = logging.getLogger(__name__)

class LocalSupabaseClient:
    """Custom client for local Supabase development with Kong key-auth"""
    
    def __init__(self, url: str, api_key: str):
        self.url = url
        self.api_key = api_key
        self.headers = {
            'apikey': api_key,
            'Content-Type': 'application/json'
        }
    
    def table(self, table_name: str):
        return LocalTableClient(self.url, table_name, self.headers)
    
    def rpc(self, function_name: str, params: dict):
        """Execute a stored procedure or function via REST API"""
        return LocalRPCBuilder(self.url, self.headers, function_name, params)

class LocalTableClient:
    """Custom table client for local development"""
    
    def __init__(self, base_url: str, table_name: str, headers: dict):
        self.base_url = base_url
        self.table_name = table_name
        self.headers = headers
        self.endpoint = f"{base_url}/rest/v1/{table_name}"
    
    def select(self, columns: str = "*"):
        return LocalQueryBuilder(self.endpoint, self.headers, columns)
    
    def insert(self, data: dict):
        return LocalInsertBuilder(self.endpoint, self.headers, data)
    
    def update(self, data: dict):
        return LocalUpdateBuilder(self.endpoint, self.headers, data)
    
    def eq(self, column: str, value: Any):
        return LocalQueryBuilder(self.endpoint, self.headers, "*").eq(column, value)

    def delete(self):
        return LocalDeleteBuilder(self.endpoint, self.headers)

class LocalQueryBuilder:
    """Custom query builder for local development"""
    
    def __init__(self, endpoint: str, headers: dict, columns: str):
        self.endpoint = endpoint
        self.headers = headers
        self.columns = columns
        self.params = {}
    
    def eq(self, column: str, value: Any):
        self.params[f"{column}"] = f"eq.{value}"
        return self
    
    def ilike(self, column: str, value: Any):
        """Case-insensitive pattern matching"""
        self.params[f"{column}"] = f"ilike.{value}"
        return self
    
    def limit(self, count: int):
        self.params["limit"] = str(count)
        return self
    
    def execute(self):
        params = "&".join([f"{k}={v}" for k, v in self.params.items()])
        url = f"{self.endpoint}?select={self.columns}"
        if params:
            url += f"&{params}"
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            return type('Response', (), {'data': response.json()})()

class LocalInsertBuilder:
    """Custom insert builder for local development"""
    
    def __init__(self, endpoint: str, headers: dict, data: dict):
        self.endpoint = endpoint
        self.headers = headers
        self.data = data
    
    def execute(self):
        with httpx.Client(timeout=30.0) as client:
            # Add select=* to get the inserted record back
            insert_url = f"{self.endpoint}?select=*"
            response = client.post(
                insert_url,
                headers=self.headers,
                json=self.data
            )
            response.raise_for_status()
            
            # Handle empty response (common with PostgREST)
            if response.text.strip():
                return type('Response', (), {'data': response.json()})()
            else:
                # Return empty data for successful insert with no response
                return type('Response', (), {'data': []})()

class LocalUpdateBuilder:
    """Custom update builder for local development"""
    
    def __init__(self, endpoint: str, headers: dict, data: dict):
        self.endpoint = endpoint
        self.headers = headers
        self.data = data
        self.params = {}
    
    def eq(self, column: str, value: Any):
        self.params[f"{column}"] = f"eq.{value}"
        return self
    
    def execute(self):
        params = "&".join([f"{k}={v}" for k, v in self.params.items()])
        url = self.endpoint
        if params:
            url += f"?{params}"
        
        with httpx.Client(timeout=30.0) as client:
            # Add select=* to get the updated record back
            update_url = f"{url}&select=*"
            response = client.patch(
                update_url,
                headers=self.headers,
                json=self.data
            )
            response.raise_for_status()
            
            # Handle empty response (common with PostgREST)
            if response.text.strip():
                return type('Response', (), {'data': response.json()})()
            else:
                # Return empty data for successful update with no response
                return type('Response', (), {'data': []})()

class LocalDeleteBuilder:
    """Custom delete builder for local development"""
    def __init__(self, endpoint: str, headers: dict):
        self.endpoint = endpoint
        self.headers = headers
        self.params = {}
    
    def eq(self, column: str, value: Any):
        self.params[f"{column}"] = f"eq.{value}"
        return self
    
    def neq(self, column: str, value: Any):
        self.params[f"{column}"] = f"neq.{value}"
        return self
    
    def execute(self):
        params = "&".join([f"{k}={v}" for k, v in self.params.items()])
        url = self.endpoint
        if params:
            url += f"?{params}"
        with httpx.Client(timeout=30.0) as client:
            response = client.delete(url, headers=self.headers)
            response.raise_for_status()
            # Return a dummy response object for compatibility
            return type('Response', (), {'data': response.json() if response.text.strip() else []})()

class LocalRPCBuilder:
    """Custom RPC builder for local development"""
    def __init__(self, base_url: str, headers: dict, function_name: str, params: dict):
        self.base_url = base_url
        self.headers = headers
        self.function_name = function_name
        self.params = params
        self.endpoint = f"{base_url}/rest/v1/rpc/{function_name}"
    
    def execute(self):
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                self.endpoint,
                headers=self.headers,
                json=self.params
            )
            response.raise_for_status()
            
            # Handle empty response (common with PostgREST)
            if response.text.strip():
                return type('Response', (), {'data': response.json()})()
            else:
                # Return empty data for successful execution with no response
                return type('Response', (), {'data': []})()

class SupabaseClient:
    """
    Client for interacting with Supabase database
    """
    _instance = None
    _client: Optional[SupabaseBaseClient] = None
    _local_client: Optional[LocalSupabaseClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
            cls._instance._setup()
        return cls._instance

    def _setup(self):
        """Set up the Supabase client with the correct credentials"""
        # Load environment variables from project root .env
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        print(f"Loading environment variables from {env_path}")
        load_dotenv(env_path)

        # Get the Supabase URL - try multiple possible names
        supabase_url = os.getenv('SUPABASE_URL')
        if not supabase_url:
            supabase_url = os.getenv('SUPABASE_PUBLIC_URL')
        if not supabase_url:
            supabase_url = 'http://localhost:8000'
            
        logger.debug(f"Using Supabase URL: {supabase_url}")

        # Get the Supabase service role key - try multiple possible names
        service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        if not service_role_key:
            service_role_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not service_role_key:
            # Try anon key as fallback
            service_role_key = os.getenv('SUPABASE_ANON_KEY')
            
        if not service_role_key:
            raise ValueError("No Supabase key found! Please set SUPABASE_SERVICE_ROLE_KEY, SUPABASE_SERVICE_KEY, or SUPABASE_ANON_KEY in your environment variables.")
        
        logger.debug(f"Using Supabase key: {service_role_key[:10]}...")

        try:
            # For local development, use custom client with Kong key-auth
            if 'localhost' in supabase_url or '127.0.0.1' in supabase_url:
                self._local_client = LocalSupabaseClient(supabase_url, service_role_key)
                # Test the connection
                self._local_client.table('dropbox_accounts').select('count').execute()
                logger.info("Successfully connected to local Supabase")
            else:
                # For cloud Supabase, use the standard client
                self._client = create_client(supabase_url, service_role_key)
                # Test the connection
                self._client.table('dropbox_accounts').select('count').execute()
                logger.info("Successfully connected to Supabase")
        except Exception as e:
            print(f"[DEBUG] Outer exception caught: {type(e).__name__}: {str(e)}")
            print(f"[DEBUG] Exception args: {e.args}")
            logger.error(f"Failed to connect to Supabase: {str(e)}")
            logger.error(f"URL: {supabase_url}")
            logger.error(f"Key type: {'Service Role' if 'service_role' in service_role_key else 'Anon'}")
            raise

    @property
    def client(self) -> SupabaseBaseClient:
        """Get the Supabase client instance"""
        if self._local_client:
            return self._local_client
        return self._client

    def _serialize_dates(self, obj):
        """Serialize dates for database storage"""
        if isinstance(obj, dict):
            return {k: self._serialize_dates(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_dates(i) for i in obj]
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return obj

    def store_person_info(self, person: DropboxAccountApplicationInfo) -> Optional[int]:
        """Store person information and return the ID"""
        try:
            # Check if person already exists (by name and address)
            if person.first_name and person.last_name:
                existing_response = self.client.table('dropbox_account_application_info').select('id').eq('first_name', person.first_name).eq('last_name', person.last_name).execute()
                if existing_response.data and len(existing_response.data) > 0:
                    existing_id = existing_response.data[0]['id']
                    print(f"[DEBUG] Person already exists with ID: {existing_id}")
                    return existing_id
            
            # Serialize the person data
            person_data = self._serialize_dates(person.model_dump(exclude_none=True))
            print(f"[DEBUG] Inserting person info: {person_data}")
            # Insert into the database
            response = self.client.table('dropbox_account_application_info').insert(person_data).execute()
            print(f"[DEBUG] Insert response: {getattr(response, 'data', None)} | Error: {getattr(response, 'error', None)}")
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            else:
                # Insert succeeded but no data returned (common with local Supabase)
                # Query for the newly created record to get its ID
                print(f"[DEBUG] Insert succeeded but no data returned, querying for new person record...")
                new_person_response = self.client.table('dropbox_account_application_info').select('id').eq('first_name', person.first_name).eq('last_name', person.last_name).execute()
                if new_person_response.data and len(new_person_response.data) > 0:
                    person_id = new_person_response.data[0]['id']
                    print(f"[DEBUG] Found newly created person ID: {person_id}")
                    return person_id
                else:
                    logger.warning("No data returned from person_info insert and could not find newly created record")
                    return None
        except Exception as e:
            logger.error(f"Error storing person info: {str(e)}")
            print(f"[ERROR] Exception in store_person_info: {e}")
            return None

    def store_application_file(self, app_file: DropboxAccountApplicationFile, dropbox_account_id: int, folder_name: str = None) -> Optional[int]:
        """Store application file data and return the file ID"""
        folder_info = f" in folder '{folder_name}'" if folder_name else ""
        try:
            # First store owner info if present
            owner_id = None
            if app_file.owner and (app_file.owner.first_name or app_file.owner.last_name):
                owner_id = self.store_person_info(app_file.owner)
            # Store joint owner info if present
            joint_owner_id = None
            if app_file.joint_owner and (app_file.joint_owner.first_name or app_file.joint_owner.last_name):
                joint_owner_id = self.store_person_info(app_file.joint_owner)
            # Prepare application file data
            file_data = {
                'file_name': app_file.file_name,
                'file_path': app_file.file_path,
                'application_type': app_file.application_type.value,
                'status': app_file.status.value,
                'owner_id': owner_id,
                'joint_owner_id': joint_owner_id,
                'notes': app_file.notes,
                'extracted_text': app_file.extracted_text,
                'processing_timestamp': app_file.processing_timestamp.isoformat() if app_file.processing_timestamp else None,
                'ocr_confidence': app_file.ocr_confidence,
                'lm_studio_model_used': app_file.lm_studio_model_used,
                'processing_duration_seconds': app_file.processing_duration_seconds,
                'dropbox_account_id': dropbox_account_id
            }
            file_data = self._serialize_dates(file_data)
            
            # Insert into the database
            response = self.client.table('dropbox_account_application_files').insert(file_data).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            else:
                # Insert succeeded but no data returned (common with local Supabase/PostgREST)
                # Query for the newly created record to get its ID
                logger.info(f"Insert succeeded but no data returned for file {app_file.file_name}{folder_info}, querying for new record...")
                new_file_response = self.client.table('dropbox_account_application_files').select('id').eq('file_name', app_file.file_name).eq('dropbox_account_id', dropbox_account_id).limit(1).execute()
                
                if new_file_response.data and len(new_file_response.data) > 0:
                    file_id = new_file_response.data[0]['id']
                    logger.info(f"Found newly created application file with ID: {file_id}")
                    return file_id
                else:
                    logger.warning(f"No data returned from application_files insert for file {app_file.file_name}{folder_info}")
                    return None
        except Exception as e:
            logger.error(f"Error storing application file {app_file.file_name}{folder_info}: {str(e)}")
            return None

    def store_dropbox_account_with_files(self, account: DropboxAccountWithFiles, force: bool = False, update_existing: bool = True) -> Optional[int]:
        """Store dropbox account and its application files. 
        
        Args:
            account: The DropboxAccountWithFiles object containing account and file data
            force: If True, delete existing account and re-insert (overwrites all data)
            update_existing: If True, update existing account fields instead of only inserting new ones
        
        Returns:
            The account ID if successful, None otherwise
        """
        logger.info(f"Store in database: dropbox account with files for account: {account.folder}")
        logger.info(f"Force mode: {force}, Update existing: {update_existing}")
        
        try:
            # First check if the account already exists using the same approach as search script
            # Get all accounts and filter manually to avoid issues with special characters in folder names
            all_accounts_response = self.client.table('dropbox_accounts').select('*').execute()
            account_id = None
            account_exists = False
            
            if all_accounts_response.data:
                # Filter results manually for exact matching (like the search script does)
                matching_accounts = [acc for acc in all_accounts_response.data 
                                   if acc.get('folder') == account.folder]
                
                if matching_accounts:
                    account_id = matching_accounts[0]['id']
                    account_exists = True
                    logger.info(f"Existing account found for folder: {account.folder}, ID: {account_id}")
                else:
                    logger.info(f"No existing account found for folder: {account.folder}")
            else:
                logger.info(f"No accounts found in database")
            
            if account_exists and force:
                logger.info(f"Force flag is set. Deleting account ID: {account_id} and all related files before re-inserting.")
                self.delete_application_files_for_folder(account.folder)
                self.delete_client_list_info_for_folder(account.folder)
                self.client.table('dropbox_accounts').delete().eq('id', account_id).execute()
                account_id = None
                account_exists = False
            
            # Prepare account data
            account_data = {
                'folder': account.folder,
                'first_name': account.first_name,
                'middle_name': account.middle_name,
                'last_name': account.last_name,
                'total_account_application_files': account.total_account_application_files,
                'processed_account_application_files': account.processed_account_application_files,
                'failed_account_application_files': account.failed_account_application_files,
                'processing_timestamp': account.processing_timestamp.isoformat() if account.processing_timestamp else None
            }
            account_data = self._serialize_dates(account_data)

            # Always update if exists, insert if not
            if account_exists and update_existing:
                logger.info(f"Updating existing account ID: {account_id} with data: {account_data}")
                update_response = self.client.table('dropbox_accounts').update(account_data).eq('id', account_id).execute()
                logger.info(f"Update response: {getattr(update_response, 'data', None)} | Error: {getattr(update_response, 'error', None)}")
                if not update_response.data:
                    logger.warning(f"Update succeeded but no data returned for account ID: {account_id}")
            elif not account_exists:
                logger.info(f"Inserting new dropbox account: {account_data}")
                response = self.client.table('dropbox_accounts').insert(account_data).execute()
                logger.info(f"Insert response: {getattr(response, 'data', None)} | Error: {getattr(response, 'error', None)}")
                if response.data and len(response.data) > 0:
                    account_id = response.data[0]['id']
                    logger.info(f"Created new account ID: {account_id}")
                else:
                    logger.info("Insert succeeded but no data returned, querying for new record...")
                    new_account_response = self.client.table('dropbox_accounts').select('id').eq('folder', account.folder).execute()
                    if new_account_response.data and len(new_account_response.data) > 0:
                        account_id = new_account_response.data[0]['id']
                        logger.info(f"Found newly created account ID: {account_id}")
                    else:
                        logger.error(f"Failed to insert dropbox account: Could not find newly created record")
                        return None
            else:
                logger.info(f"Using existing account ID: {account_id} for folder: {account.folder} (no updates)")

            # Store client list info if available
            try:
                if account.client_list_info:
                    logger.info(f"Storing client list info for account ID: {account_id}")
                    client_list_id = self.store_dropbox_client_list_info(account.client_list_info, account_id, account.folder)
                    if client_list_id:
                        logger.info(f"Successfully stored client list info with ID: {client_list_id}")
                    else:
                        logger.warning(f"Failed to store client list info for account ID: {account_id}")
                else:
                    logger.info("No client list info available to store")
            except Exception as e:
                logger.error(f"Exception in store_dropbox_client_list_info: {e}")
                import traceback; logger.error(traceback.format_exc())
                return None

            # Store each application file
            try:
                for app_file in account.application_files:
                    logger.info(f"Storing application file: {app_file.file_name} for account ID: {account_id}")
                    file_id = self.store_application_file(app_file, account_id, account.folder)
                    if file_id:
                        logger.info(f"Successfully stored application file with ID: {file_id}")
                    else:
                        logger.warning(f"Failed to store application file: {app_file.file_name} in folder '{account.folder}'")
            except Exception as e:
                logger.error(f"Exception in store_application_file: {e}")
                import traceback; logger.error(traceback.format_exc())
                return None
            
            # Get client list info for this account
            try:
                client_list_info = self.get_client_list_info_by_folder(account.folder)
            except Exception as e:
                logger.error(f"Exception in get_client_list_info_by_folder: {e}")
                import traceback; logger.error(traceback.format_exc())
                return None
            
            # Create the account with files
            account = DropboxAccountWithFiles(
                folder=account_data['folder'],
                first_name=account_data.get('first_name'),
                middle_name=account_data.get('middle_name'),
                last_name=account_data.get('last_name'),
                application_files=account.application_files,
                client_list_info=client_list_info,
                total_account_application_files=account_data.get('total_account_application_files', 0),
                processed_account_application_files=account_data.get('processed_account_application_files', 0),
                failed_account_application_files=account_data.get('failed_account_application_files', 0),
                processing_timestamp=datetime.fromisoformat(account_data['processing_timestamp']) if account_data.get('processing_timestamp') else None
            )
            
            # Calculate and store the best account information
            try:
                logger.info(f"Calculating and storing best account info for account ID: {account_id}")
                best_info_id = self.calculate_and_store_best_account_info(account_id, account.folder)
                if best_info_id:
                    logger.info(f"Successfully stored best account info with ID: {best_info_id}")
                else:
                    logger.warning(f"Failed to store best account info for account ID: {account_id}")
            except Exception as e:
                logger.error(f"Exception in calculate_and_store_best_account_info: {e}")
                import traceback; logger.error(traceback.format_exc())
                return None

            return account_id
            
        except Exception as e:
            logger.error(f"Error storing dropbox account with files: {str(e)}")
            logger.error(f"Exception in store_dropbox_account_with_files: {e}")
            return None

    def get_application_files_by_folder(self, folder_name: str) -> Optional[DropboxAccountWithFiles]:
        """Get all application files for a specific folder"""
        try:
            # Get all dropbox accounts and filter manually to handle special characters
            all_accounts_response = self.client.table('dropbox_accounts').select('*').execute()
            
            if not all_accounts_response.data:
                logger.warning(f"No dropbox accounts found")
                return None
            
            # Find the account with matching folder name
            matching_account = None
            for account in all_accounts_response.data:
                if account['folder'] == folder_name:
                    matching_account = account
                    break
            
            if not matching_account:
                logger.warning(f"No dropbox account found for folder: {folder_name}")
                return None
            
            account_data = matching_account
            
            # Get application files for this account
            files_response = self.client.table('dropbox_account_application_files').select('*').eq('dropbox_account_id', account_data['id']).execute()
            
            # Get person info for owners and joint owners
            person_ids = set()
            for file_data in files_response.data:
                if file_data.get('owner_id'):
                    person_ids.add(file_data['owner_id'])
                if file_data.get('joint_owner_id'):
                    person_ids.add(file_data['joint_owner_id'])
            
            person_info_map = {}
            if person_ids:
                # Get all person info in one query
                person_response = self.client.table('dropbox_account_application_info').select('*').execute()
                for person in person_response.data:
                    person_info_map[person['id']] = person
            
            # Build the application files
            application_files = []
            for file_data in files_response.data:
                # Get owner info
                owner = DropboxAccountApplicationInfo()
                if file_data.get('owner_id') and file_data['owner_id'] in person_info_map:
                    owner_data = person_info_map[file_data['owner_id']]
                    owner = DropboxAccountApplicationInfo(
                        first_name=owner_data.get('first_name'),
                        last_name=owner_data.get('last_name'),
                        date_of_birth=datetime.fromisoformat(owner_data['date_of_birth']).date() if owner_data.get('date_of_birth') else None,
                        gender=owner_data.get('gender'),
                        mailing_address_street=owner_data.get('mailing_address_street'),
                        mailing_address_city=owner_data.get('mailing_address_city'),
                        mailing_address_state=owner_data.get('mailing_address_state'),
                        mailing_address_zip=owner_data.get('mailing_address_zip'),
                        phone_number=owner_data.get('phone_number'),
                        email_address=owner_data.get('email_address'),
                        ocr_method=owner_data.get('ocr_method')
                    )
                
                # Get joint owner info
                joint_owner = DropboxAccountApplicationInfo()
                if file_data.get('joint_owner_id') and file_data['joint_owner_id'] in person_info_map:
                    joint_owner_data = person_info_map[file_data['joint_owner_id']]
                    joint_owner = DropboxAccountApplicationInfo(
                        first_name=joint_owner_data.get('first_name'),
                        last_name=joint_owner_data.get('last_name'),
                        date_of_birth=datetime.fromisoformat(joint_owner_data['date_of_birth']).date() if joint_owner_data.get('date_of_birth') else None,
                        gender=joint_owner_data.get('gender'),
                        mailing_address_street=joint_owner_data.get('mailing_address_street'),
                        mailing_address_city=joint_owner_data.get('mailing_address_city'),
                        mailing_address_state=joint_owner_data.get('mailing_address_state'),
                        mailing_address_zip=joint_owner_data.get('mailing_address_zip'),
                        phone_number=joint_owner_data.get('phone_number'),
                        email_address=joint_owner_data.get('email_address'),
                        ocr_method=joint_owner_data.get('ocr_method')
                    )
                
                # Create application file object
                app_file = DropboxAccountApplicationFile(
                    file_name=file_data['file_name'],
                    file_path=file_data.get('file_path'),
                    application_type=ApplicationType(file_data.get('application_type', 'Unknown')),
                    status=ApplicationStatus(file_data.get('status', 'Processed')),
                    owner=owner,
                    joint_owner=joint_owner,
                    notes=file_data.get('notes', []),
                    extracted_text=file_data.get('extracted_text'),
                    processing_timestamp=datetime.fromisoformat(file_data['processing_timestamp']) if file_data.get('processing_timestamp') else None,
                    ocr_confidence=file_data.get('ocr_confidence'),
                    lm_studio_model_used=file_data.get('lm_studio_model_used'),
                    processing_duration_seconds=file_data.get('processing_duration_seconds')
                )
                application_files.append(app_file)
            
            # Get client list info for this account
            client_list_info = self.get_client_list_info_by_folder(folder_name)
            
            # Create the account with files
            account = DropboxAccountWithFiles(
                folder=account_data['folder'],
                first_name=account_data.get('first_name'),
                middle_name=account_data.get('middle_name'),
                last_name=account_data.get('last_name'),
                application_files=application_files,
                client_list_info=client_list_info,
                total_account_application_files=account_data.get('total_account_application_files', 0),
                processed_account_application_files=account_data.get('processed_account_application_files', 0),
                failed_account_application_files=account_data.get('failed_account_application_files', 0),
                processing_timestamp=datetime.fromisoformat(account_data['processing_timestamp']) if account_data.get('processing_timestamp') else None
            )
            
            return account
            
        except Exception as e:
            logger.error(f"Error getting application files by folder: {str(e)}")
            return None

    def check_application_file_exists(self, folder_name: str, file_name: str) -> bool:
        """Check if a specific application file already exists for a folder"""
        try:
            # Get all dropbox accounts and filter manually to handle special characters
            all_accounts_response = self.client.table('dropbox_accounts').select('*').execute()
            
            if not all_accounts_response.data:
                return False
            
            # Find the account with matching folder name
            matching_account = None
            for account in all_accounts_response.data:
                if account['folder'] == folder_name:
                    matching_account = account
                    break
            
            if not matching_account:
                return False
            
            account_id = matching_account['id']
            
            # Check if the specific file exists
            files_response = self.client.table('dropbox_account_application_files').select('id').eq('dropbox_account_id', account_id).eq('file_name', file_name).execute()
            
            return len(files_response.data) > 0
            
        except Exception as e:
            logger.error(f"Error checking application file exists: {str(e)}")
            return False

    def check_application_files_exist(self, folder_name: str) -> bool:
        """Check if application files exist for a folder"""
        try:
            # Get all dropbox accounts and filter manually to handle special characters
            all_accounts_response = self.client.table('dropbox_accounts').select('*').execute()
            
            if not all_accounts_response.data:
                return False
            
            # Find the account with matching folder name
            matching_account = None
            for account in all_accounts_response.data:
                if account['folder'] == folder_name:
                    matching_account = account
                    break
            
            if not matching_account:
                return False
            
            account_id = matching_account['id']
            
            # Check if there are any application files
            files_response = self.client.table('dropbox_account_application_files').select('id').eq('dropbox_account_id', account_id).execute()
            
            return len(files_response.data) > 0
            
        except Exception as e:
            logger.error(f"Error checking application files exist: {str(e)}")
            return False

    def delete_application_files_for_folder(self, folder_name: str) -> bool:
        """Delete all application files for a specific folder"""
        try:
            # Get all dropbox accounts and filter manually to handle special characters
            all_accounts_response = self.client.table('dropbox_accounts').select('*').execute()
            
            if not all_accounts_response.data:
                logger.warning(f"No dropbox accounts found")
                return False
            
            # Find the account with matching folder name
            matching_account = None
            for account in all_accounts_response.data:
                if account['folder'] == folder_name:
                    matching_account = account
                    break
            
            if not matching_account:
                logger.warning(f"No dropbox account found for folder: {folder_name}")
                return False
            
            account_id = matching_account['id']
            
            # Get all application files for this account to find person IDs
            files_response = self.client.table('dropbox_account_application_files').select('owner_id,joint_owner_id').eq('dropbox_account_id', account_id).execute()
            
            # Collect person IDs to delete
            person_ids = set()
            for file_data in files_response.data:
                if file_data.get('owner_id'):
                    person_ids.add(file_data['owner_id'])
                if file_data.get('joint_owner_id'):
                    person_ids.add(file_data['joint_owner_id'])
            
            # Delete application files
            self.client.table('dropbox_account_application_files').delete().eq('dropbox_account_id', account_id).execute()
            
            # Delete person info records
            for person_id in person_ids:
                if person_id:
                    self.client.table('dropbox_account_application_info').delete().eq('id', person_id).execute()
            
            logger.info(f"Deleted application files for folder: {folder_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting application files for folder: {str(e)}")
            return False

    def generate_account_summary(self, folder_name: str) -> str:
        """Generate a summary of account data for a folder"""
        try:
            summary_lines = []
            summary_lines.append(f"📁 **Account Summary for: {folder_name}**")
            summary_lines.append("=" * 50)
            
            # Get the account with files
            account = self.get_application_files_by_folder(folder_name)
            
            if not account:
                summary_lines.append("❌ No account data found for this folder")
                return "\n".join(summary_lines)
            
            # Account info
            summary_lines.append(f"👤 **Account Holder:** {account.first_name or 'N/A'} {account.middle_name or ''} {account.last_name or 'N/A'}")
            summary_lines.append(f"📊 **File Statistics:**")
            summary_lines.append(f"   • Total Files: {account.total_account_application_files}")
            summary_lines.append(f"   • Processed: {account.processed_account_application_files}")
            summary_lines.append(f"   • Failed: {account.failed_account_application_files}")
            
            if account.processing_timestamp:
                summary_lines.append(f"⏰ **Last Processed:** {account.processing_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Application files
            if account.application_files:
                summary_lines.append(f"\n📄 **Application Files ({len(account.application_files)}):**")
                
                for i, app_file in enumerate(account.application_files, 1):
                    summary_lines.append(f"\n{i}. **{app_file.file_name}**")
                    summary_lines.append(f"   📋 Type: {app_file.application_type.value}")
                    summary_lines.append(f"   ✅ Status: {app_file.status.value}")
                    
                    if app_file.owner and (app_file.owner.first_name or app_file.owner.last_name):
                        summary_lines.append(f"   👤 Owner: {app_file.owner.first_name or ''} {app_file.owner.last_name or ''}")
                        if app_file.owner.date_of_birth:
                            summary_lines.append(f"      📅 DOB: {app_file.owner.date_of_birth}")
                        if app_file.owner.phone_number:
                            summary_lines.append(f"      📞 Phone: {app_file.owner.phone_number}")
                    
                    if app_file.joint_owner and (app_file.joint_owner.first_name or app_file.joint_owner.last_name):
                        summary_lines.append(f"   👥 Joint Owner: {app_file.joint_owner.first_name or ''} {app_file.joint_owner.last_name or ''}")
                        if app_file.joint_owner.date_of_birth:
                            summary_lines.append(f"      📅 DOB: {app_file.joint_owner.date_of_birth}")
                        if app_file.joint_owner.phone_number:
                            summary_lines.append(f"      📞 Phone: {app_file.joint_owner.phone_number}")
                    
                    if app_file.notes:
                        summary_lines.append(f"   📝 Notes: {', '.join(app_file.notes)}")
                    
                    if app_file.processing_duration_seconds:
                        summary_lines.append(f"   ⏱️ Processing Time: {app_file.processing_duration_seconds:.2f}s")
            else:
                summary_lines.append("\n📄 **Application Files:** None found")
            
            return "\n".join(summary_lines)
            
        except Exception as e:
            summary_lines = []
            summary_lines.append(f"📁 **Account Summary for: {folder_name}**")
            summary_lines.append("=" * 50)
            summary_lines.append(f"\n❌ Error generating summary: {str(e)}")
            return "\n".join(summary_lines)

    def generate_search_results_summary(self, folder_name: str, search_criteria: dict = None) -> str:
        """Generate a summary of search results for a folder"""
        try:
            summary_lines = []
            summary_lines.append(f"🔍 **Search Results Summary for: {folder_name}**")
            summary_lines.append("=" * 50)
            
            if search_criteria:
                summary_lines.append(f"🔎 **Search Criteria:**")
                for key, value in search_criteria.items():
                    summary_lines.append(f"   • {key}: {value}")
                summary_lines.append("")
            
            # Get the account with files
            account = self.get_application_files_by_folder(folder_name)
            
            if not account:
                summary_lines.append("❌ No account data found for this folder")
                return "\n".join(summary_lines)
            
            # Filter files based on search criteria
            matching_files = account.application_files
            
            if search_criteria:
                matching_files = []
                for app_file in account.application_files:
                    matches = True
                    
                    # Check owner name
                    if 'owner_name' in search_criteria:
                        owner_name = f"{app_file.owner.first_name or ''} {app_file.owner.last_name or ''}".strip()
                        if search_criteria['owner_name'].lower() not in owner_name.lower():
                            matches = False
                    
                    # Check joint owner name
                    if 'joint_owner_name' in search_criteria:
                        joint_owner_name = f"{app_file.joint_owner.first_name or ''} {app_file.joint_owner.last_name or ''}".strip()
                        if search_criteria['joint_owner_name'].lower() not in joint_owner_name.lower():
                            matches = False
                    
                    # Check application type
                    if 'application_type' in search_criteria:
                        if app_file.application_type.value.lower() != search_criteria['application_type'].lower():
                            matches = False
                    
                    if matches:
                        matching_files.append(app_file)
            
            summary_lines.append(f"📊 **Results:** {len(matching_files)} files found")
            
            if matching_files:
                for i, app_file in enumerate(matching_files, 1):
                    summary_lines.append(f"\n{i}. **{app_file.file_name}**")
                    summary_lines.append(f"   📋 Type: {app_file.application_type.value}")
                    
                    if app_file.owner and (app_file.owner.first_name or app_file.owner.last_name):
                        summary_lines.append(f"   👤 Owner: {app_file.owner.first_name or ''} {app_file.owner.last_name or ''}")
                    
                    if app_file.joint_owner and (app_file.joint_owner.first_name or app_file.joint_owner.last_name):
                        summary_lines.append(f"   👥 Joint Owner: {app_file.joint_owner.first_name or ''} {app_file.joint_owner.last_name or ''}")
            else:
                summary_lines.append("\n📄 No matching files found")
            
            return "\n".join(summary_lines)
            
        except Exception as e:
            summary_lines = []
            summary_lines.append(f"🔍 **Search Results Summary for: {folder_name}**")
            summary_lines.append("=" * 50)
            summary_lines.append(f"\n❌ Error generating search summary: {str(e)}")
            return "\n".join(summary_lines)

    def insert_application_file(self, app_file: DropboxAccountApplicationFile, account_id: int) -> Dict:
        """Insert an application file"""
        return self.client.insert_application_file(app_file, account_id)
    
    def get_dropbox_accounts(self) -> List[Dict]:
        """Get all dropbox accounts"""
        return self.client.get_dropbox_accounts()
    
    def get_application_files(self) -> List[Dict]:
        """Get all application files"""
        return self.client.get_application_files()
    
    def get_person_info(self) -> List[Dict]:
        """Get all person info"""
        return self.client.get_person_info()
    
    def delete_dropbox_account(self, account_id: int) -> Dict:
        """Delete a dropbox account"""
        return self.client.delete_dropbox_account(account_id)
    
    def delete_application_file(self, file_id: int) -> Dict:
        """Delete an application file"""
        return self.client.delete_application_file(file_id)
    
    def delete_person_info(self, person_id: int) -> Dict:
        """Delete person info"""
        return self.client.delete_person_info(person_id)

    def store_dropbox_client_list_info(self, client_list_info: DropboxAccountClientListInfo, dropbox_account_id: int, dropbox_account_folder_name: str = None) -> Optional[int]:
        """Store client list file data and return the client list info ID"""
        folder_name = dropbox_account_folder_name or f"account_id_{dropbox_account_id}"
        logger.info(f"Store in Database: dropbox client list data for account: {folder_name}, dropbox_account_id: {dropbox_account_id}")
        try:
            # First, delete any existing client list info for this account to avoid duplicates
            logger.info(f"Deleting existing client list info for account ID: {dropbox_account_id}")
            delete_response = self.client.table('dropbox_account_client_list_info').delete().eq('dropbox_account_id', dropbox_account_id).execute()
            logger.info(f"Deleted {len(delete_response.data) if delete_response.data else 0} existing records")
            
            # Prepare client list data
            client_list_data = {
                'dropbox_account_id': dropbox_account_id,
                'account_name': client_list_info.account_name,
                'first_name': client_list_info.first_name,
                'middle_name': client_list_info.middle_name,
                'last_name': client_list_info.last_name,
                'birthdate': client_list_info.birthdate.isoformat() if client_list_info.birthdate else None,
                'gender': client_list_info.gender,
                'phone': client_list_info.phone,
                'address': client_list_info.address,
                'city': client_list_info.city,
                'state': client_list_info.state,
                'zip_code': client_list_info.zip_code,
                'email': client_list_info.email,
                'additional_info': client_list_info.additional_info,
                'match_status': client_list_info.match_status,
                'drivers_license_data': client_list_info.drivers_license_data,
                'search_info': client_list_info.search_info
            }
            
            client_list_data = self._serialize_dates(client_list_data)
            print(f"[DEBUG] Inserting client list info: {client_list_data}")
            
            # Insert into the database
            response = self.client.table('dropbox_account_client_list_info').insert(client_list_data).execute()
            print(f"[DEBUG] Insert response: {getattr(response, 'data', None)} | Error: {getattr(response, 'error', None)}")
            
            if response.data and len(response.data) > 0:
                client_list_id = response.data[0]['id']
                logger.info(f"Successfully stored client list info with ID: {client_list_id}")
                return client_list_id
            else:
                # If no data returned but no error, try to query for the newly created record
                logger.warning("No data returned from client_list_info insert, querying for new record...")
                query_response = self.client.table('dropbox_account_client_list_info').select('id').eq('dropbox_account_id', dropbox_account_id).limit(1).execute()
                
                if query_response.data and len(query_response.data) > 0:
                    client_list_id = query_response.data[0]['id']
                    logger.info(f"Found newly created client list info with ID: {client_list_id}")
                    return client_list_id
                else:
                    logger.error("Failed to find newly created client list info record")
                    return None
        except Exception as e:
            # Check if the error is due to the table not existing
            error_str = str(e).lower()
            if 'does not exist' in error_str or 'relation' in error_str or '404' in error_str:
                # Table doesn't exist, which is expected in the current schema
                logger.debug(f"Client list info table not available, skipping storage for account ID: {dropbox_account_id}")
                return None
            else:
                # Some other error occurred
                logger.error(f"Error storing client list info: {str(e)}")
                print(f"[ERROR] Exception in store_client_list_info: {e}")
                return None

    def get_client_list_info_by_folder(self, folder_name: str) -> Optional[DropboxAccountClientListInfo]:
        """Get client list info for a specific folder"""
        try:
            # Get all dropbox accounts and filter manually to handle special characters
            all_accounts_response = self.client.table('dropbox_accounts').select('*').execute()
            
            if not all_accounts_response.data:
                logger.warning(f"No dropbox accounts found")
                return None
            
            # Find the account with matching folder name
            matching_account = None
            for account in all_accounts_response.data:
                if account['folder'] == folder_name:
                    matching_account = account
                    break
            
            if not matching_account:
                logger.warning(f"No dropbox account found for folder: {folder_name}")
                return None
            
            account_id = matching_account['id']
            
            # Get client list info for this account
            client_list_response = self.client.table('dropbox_account_client_list_info').select('*').eq('dropbox_account_id', account_id).execute()
            
            if not client_list_response.data or len(client_list_response.data) == 0:
                logger.info(f"No client list info found for folder: {folder_name}")
                return None
            
            client_list_data = client_list_response.data[0]
            
            # Convert to Pydantic model
            client_list_info = DropboxAccountClientListInfo(
                account_name=client_list_data.get('account_name'),
                first_name=client_list_data.get('first_name'),
                middle_name=client_list_data.get('middle_name'),
                last_name=client_list_data.get('last_name'),
                birthdate=datetime.fromisoformat(client_list_data['birthdate']).date() if client_list_data.get('birthdate') else None,
                gender=client_list_data.get('gender'),
                phone=client_list_data.get('phone'),
                address=client_list_data.get('address'),
                city=client_list_data.get('city'),
                state=client_list_data.get('state'),
                zip_code=client_list_data.get('zip_code'),
                email=client_list_data.get('email'),
                additional_info=client_list_data.get('additional_info'),
                match_status=client_list_data.get('match_status'),
                drivers_license_data=client_list_data.get('drivers_license_data', {}),
                search_info=client_list_data.get('search_info', {})
            )
            
            return client_list_info
            
        except Exception as e:
            # Check if the error is due to the table not existing
            error_str = str(e).lower()
            if 'does not exist' in error_str or 'relation' in error_str or '404' in error_str:
                # Table doesn't exist, which is expected in the current schema
                logger.debug(f"Client list info table not available for folder: {folder_name}")
                return None
            else:
                # Some other error occurred
                logger.error(f"Error getting client list info by folder: {str(e)}")
                return None

    def delete_client_list_info_for_folder(self, folder_name: str) -> bool:
        """Delete client list info for a specific folder"""
        try:
            # Get all dropbox accounts and filter manually to handle special characters
            all_accounts_response = self.client.table('dropbox_accounts').select('*').execute()
            
            if not all_accounts_response.data:
                logger.warning(f"No dropbox accounts found")
                return False
            
            # Find the account with matching folder name
            matching_account = None
            for account in all_accounts_response.data:
                if account['folder'] == folder_name:
                    matching_account = account
                    break
            
            if not matching_account:
                logger.warning(f"No dropbox account found for folder: {folder_name}")
                return False
            
            account_id = matching_account['id']
            
            # Delete client list info
            self.client.table('dropbox_account_client_list_info').delete().eq('dropbox_account_id', account_id).execute()
            
            logger.info(f"Deleted client list info for folder: {folder_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting client list info for folder: {str(e)}")
            return False

    def update_salesforce_accounts_found_count(self, folder_name: str, count: int) -> bool:
        """Update the salesforce_accounts_found_count field for a dropbox account"""
        try:
            # Get all dropbox accounts and filter manually to handle special characters
            all_accounts_response = self.client.table('dropbox_accounts').select('*').execute()
            
            if not all_accounts_response.data:
                logger.warning(f"No dropbox accounts found")
                return False
            
            # Find the account with matching folder name
            matching_account = None
            for account in all_accounts_response.data:
                if account['folder'] == folder_name:
                    matching_account = account
                    break
            
            if not matching_account:
                logger.warning(f"No dropbox account found for folder: {folder_name}")
                return False
            
            account_id = matching_account['id']
            
            # Update the salesforce_accounts_found_count field
            update_result = self.client.table('dropbox_accounts').update({
                'salesforce_accounts_found_count': count,
                'updated_at': 'now()'
            }).eq('id', account_id).execute()
            
            if update_result.data and len(update_result.data) > 0:
                logger.info(f"✅ Successfully updated salesforce_accounts_found_count for folder: {folder_name}")
                logger.info(f"   New count: {count}")
                return True
            else:
                logger.warning(f"⚠️ Failed to update salesforce_accounts_found_count for folder: {folder_name}")
                logger.warning(f"   No records were updated")
                return False
                
        except Exception as e:
            logger.error(f"Error updating salesforce_accounts_found_count: {e}")
            logger.error(f"Folder: {folder_name}, Count: {count}")
            return False

    def get_salesforce_accounts_found_count(self, folder_name: str) -> Optional[int]:
        """Get the salesforce_accounts_found_count for a dropbox account"""
        try:
            # Get all dropbox accounts and filter manually to handle special characters
            all_accounts_response = self.client.table('dropbox_accounts').select('*').execute()
            
            if not all_accounts_response.data:
                logger.warning(f"No dropbox accounts found")
                return None
            
            # Find the account with matching folder name
            matching_account = None
            for account in all_accounts_response.data:
                if account['folder'] == folder_name:
                    matching_account = account
                    break
            
            if not matching_account:
                logger.warning(f"No dropbox account found for folder: {folder_name}")
                return None
            
            count = matching_account.get('salesforce_accounts_found_count')
            logger.debug(f"Retrieved salesforce_accounts_found_count for folder {folder_name}: {count}")
            return count
                
        except Exception as e:
            logger.error(f"Error getting salesforce_accounts_found_count: {e}")
            logger.error(f"Folder: {folder_name}")
            return None

    # Salesforce Storage Methods
    def store_salesforce_account(self, account: SalesforceAccount) -> Optional[str]:
        """Store Salesforce account data and return the account ID"""
        logger.info(f"Store in Database: salesforce account data for account: {account.salesforce_account_id}")
        try:
            account_data = account.model_dump()
            account_data = self._serialize_dates(account_data)
            
            print(f"[DEBUG] Inserting Salesforce account: {account_data}")
            
            # Try to insert first, if it fails due to conflict, update instead
            try:
                response = self.client.table('salesforce_accounts').insert(account_data).execute()
                
                if response.data and len(response.data) > 0:
                    account_id = response.data[0]['salesforce_account_id']
                    print(f"[DEBUG] Created Salesforce account ID: {account_id}")
                    return account_id
                else:
                    print(f"[DEBUG] Insert succeeded but no data returned, querying for new record...")
                    new_account_response = self.client.table('salesforce_accounts').select('salesforce_account_id').eq('salesforce_account_id', account.salesforce_account_id).execute()
                    if new_account_response.data and len(new_account_response.data) > 0:
                        account_id = new_account_response.data[0]['salesforce_account_id']
                        print(f"[DEBUG] Found newly created Salesforce account ID: {account_id}")
                        return account_id
                        
            except Exception as insert_error:
                if "409" in str(insert_error) or "Conflict" in str(insert_error):
                    print(f"[DEBUG] Account already exists, updating instead: {account.salesforce_account_id}")
                    # Try to update the existing record
                    try:
                        update_response = self.client.table('salesforce_accounts').update(account_data).eq('salesforce_account_id', account.salesforce_account_id).execute()
                        if update_response.data and len(update_response.data) > 0:
                            account_id = update_response.data[0]['salesforce_account_id']
                            print(f"[DEBUG] Updated existing Salesforce account ID: {account_id}")
                            return account_id
                        else:
                            print(f"[DEBUG] Update succeeded but no data returned")
                            return account.salesforce_account_id
                    except Exception as update_error:
                        logger.error(f"Error updating existing Salesforce account: {str(update_error)}")
                        return None
                else:
                    # Re-raise if it's not a conflict error
                    raise insert_error
                    
        except Exception as e:
            logger.error(f"Error storing Salesforce account: {str(e)}")
            print(f"[ERROR] Exception in store_salesforce_account: {e}")
            return None

    def store_salesforce_household(self, household: SalesforceHousehold) -> Optional[str]:
        """Store Salesforce household data and return the household ID"""
        try:
            household_data = household.model_dump()
            household_data = self._serialize_dates(household_data)
            
            print(f"[DEBUG] Inserting Salesforce household: {household_data}")
            
            # Try to insert first, if it fails due to conflict, update instead
            try:
                response = self.client.table('salesforce_households').insert(household_data).execute()
                
                if response.data and len(response.data) > 0:
                    household_id = response.data[0]['salesforce_household_id']
                    print(f"[DEBUG] Created Salesforce household ID: {household_id}")
                    return household_id
                else:
                    print(f"[DEBUG] Insert succeeded but no data returned, querying for new record...")
                    new_household_response = self.client.table('salesforce_households').select('salesforce_household_id').eq('salesforce_household_id', household.salesforce_household_id).execute()
                    if new_household_response.data and len(new_household_response.data) > 0:
                        household_id = new_household_response.data[0]['salesforce_household_id']
                        print(f"[DEBUG] Found newly created Salesforce household ID: {household_id}")
                        return household_id
                    else:
                        logger.error(f"Failed to insert Salesforce household: Could not find newly created record")
                        return None
                        
            except Exception as insert_error:
                if "409" in str(insert_error) or "Conflict" in str(insert_error):
                    print(f"[DEBUG] Household already exists, updating instead: {household.salesforce_household_id}")
                    # Try to update the existing record
                    try:
                        update_response = self.client.table('salesforce_households').update(household_data).eq('salesforce_household_id', household.salesforce_household_id).execute()
                        if update_response.data and len(update_response.data) > 0:
                            household_id = update_response.data[0]['salesforce_household_id']
                            print(f"[DEBUG] Updated existing Salesforce household ID: {household_id}")
                            return household_id
                        else:
                            print(f"[DEBUG] Update succeeded but no data returned")
                            return household.salesforce_household_id
                    except Exception as update_error:
                        logger.error(f"Error updating existing Salesforce household: {str(update_error)}")
                        return None
                else:
                    # Re-raise if it's not a conflict error
                    raise insert_error
                    
        except Exception as e:
            logger.error(f"Error storing Salesforce household: {str(e)}")
            print(f"[ERROR] Exception in store_salesforce_household: {e}")
            return None

    def store_salesforce_household_member(self, member: SalesforceHouseholdMember) -> Optional[int]:
        """Store Salesforce household member data and return the member ID"""
        try:
            member_data = member.model_dump()
            member_data = self._serialize_dates(member_data)
            
            print(f"[DEBUG] Inserting Salesforce household member: {member_data}")
            response = self.client.table('salesforce_household_members').insert(member_data).execute()
            
            if response.data and len(response.data) > 0:
                member_id = response.data[0]['id']
                print(f"[DEBUG] Created Salesforce household member ID: {member_id}")
                return member_id
            else:
                logger.error(f"Failed to insert Salesforce household member: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error storing Salesforce household member: {str(e)}")
            print(f"[ERROR] Exception in store_salesforce_household_member: {e}")
            return None

    def store_salesforce_accounts_batch(self, accounts: List[SalesforceAccount]) -> List[str]:
        """Store multiple Salesforce accounts and return their IDs"""
        stored_ids = []
        
        for account in accounts:
            account_id = self.store_salesforce_account(account)
            if account_id:
                stored_ids.append(account_id)
            else:
                logger.warning(f"Failed to store Salesforce account: {account.account_name}")
        
        return stored_ids

    def store_dropbox_salesforce_mapping(self, mapping: DropboxSalesforceMapping) -> Optional[int]:
        """Store mapping between Dropbox and Salesforce accounts"""
        try:
            mapping_data = mapping.model_dump()
            mapping_data = self._serialize_dates(mapping_data)
            
            print(f"[DEBUG] Inserting Dropbox-Salesforce mapping: {mapping_data}")
            response = self.client.table('dropbox_salesforce_mapping').insert(mapping_data).execute()
            
            if response.data and len(response.data) > 0:
                mapping_id = response.data[0]['id']
                print(f"[DEBUG] Created mapping ID: {mapping_id}")
                return mapping_id
            else:
                logger.error(f"Failed to insert mapping: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error storing Dropbox-Salesforce mapping: {str(e)}")
            print(f"[ERROR] Exception in store_dropbox_salesforce_mapping: {e}")
            return None

    def store_sync_status(self, sync_status: SyncStatus) -> Optional[int]:
        """Store sync status between Dropbox and Salesforce accounts"""
        try:
            sync_data = sync_status.model_dump()
            sync_data = self._serialize_dates(sync_data)
            
            print(f"[DEBUG] Inserting sync status: {sync_data}")
            response = self.client.table('sync_status').insert(sync_data).execute()
            
            if response.data and len(response.data) > 0:
                sync_id = response.data[0]['id']
                print(f"[DEBUG] Created sync status ID: {sync_id}")
                return sync_id
            else:
                logger.error(f"Failed to insert sync status: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error storing sync status: {str(e)}")
            print(f"[ERROR] Exception in store_sync_status: {e}")
            return None

    def store_account_analysis(self, analysis: AccountAnalysis) -> Optional[int]:
        """Store account analysis data"""
        try:
            analysis_data = analysis.model_dump()
            analysis_data = self._serialize_dates(analysis_data)
            
            print(f"[DEBUG] Inserting account analysis: {analysis_data}")
            response = self.client.table('account_analysis').insert(analysis_data).execute()
            
            if response.data and len(response.data) > 0:
                analysis_id = response.data[0]['id']
                print(f"[DEBUG] Created account analysis ID: {analysis_id}")
                return analysis_id
            else:
                logger.error(f"Failed to insert account analysis: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error storing account analysis: {str(e)}")
            print(f"[ERROR] Exception in store_account_analysis: {e}")
            return None

    def get_salesforce_account(self, salesforce_account_id: str) -> Optional[SalesforceAccount]:
        """Get Salesforce account by ID"""
        try:
            response = self.client.table('salesforce_accounts').select('*').eq('salesforce_account_id', salesforce_account_id).execute()
            
            if response.data and len(response.data) > 0:
                account_data = response.data[0]
                return SalesforceAccount(**account_data)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting Salesforce account: {str(e)}")
            return None

    def get_salesforce_accounts_by_name(self, account_name: str) -> List[SalesforceAccount]:
        """Get Salesforce accounts by name (partial match)"""
        try:
            response = self.client.table('salesforce_accounts').select('*').ilike('account_name', f'%{account_name}%').execute()
            
            accounts = []
            for account_data in response.data:
                accounts.append(SalesforceAccount(**account_data))
            
            return accounts
            
        except Exception as e:
            logger.error(f"Error getting Salesforce accounts by name: {str(e)}")
            return []

    def update_salesforce_account(self, salesforce_account_id: str, updates: Dict[str, Any]) -> bool:
        """Update Salesforce account data"""
        try:
            updates = self._serialize_dates(updates)
            response = self.client.table('salesforce_accounts').update(updates).eq('salesforce_account_id', salesforce_account_id).execute()
            
            return response.data is not None and len(response.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating Salesforce account: {str(e)}")
            return False

    def delete_salesforce_account(self, salesforce_account_id: str) -> bool:
        """Delete Salesforce account by ID"""
        try:
            response = self.client.table('salesforce_accounts').delete().eq('salesforce_account_id', salesforce_account_id).execute()
            return response.data is not None
            
        except Exception as e:
            logger.error(f"Error deleting Salesforce account: {str(e)}")
            return False

    def delete_salesforce_accounts_by_folder_name(self, dropbox_folder_name: str) -> bool:
        """Delete Salesforce accounts associated with a specific Dropbox folder name"""
        try:
            # Generate name variations for searching (similar to search logic)
            name_variations = [
                dropbox_folder_name,
                dropbox_folder_name.replace(', ', ' '),
                dropbox_folder_name.replace(',', ' '),
                ' '.join(dropbox_folder_name.split(', ')[::-1])  # Swapped names
            ]
            
            deleted_count = 0
            found_accounts = []
            
            # First, find all accounts that match any of the name variations
            for name_variation in name_variations:
                try:
                    # Use a safer search approach - get all accounts and filter locally
                    response = self.client.table('salesforce_accounts').select('*').execute()
                    
                    if response.data:
                        for account in response.data:
                            account_name = account.get('account_name', '')
                            # Check if this account matches the name variation (case-insensitive)
                            if name_variation.lower() in account_name.lower():
                                found_accounts.append(account)
                                logger.info(f"Found account to delete: {account_name}")
                            
                except Exception as e:
                    logger.warning(f"Error searching for accounts with name variation '{name_variation}': {e}")
                    continue
            
            # Remove duplicates based on salesforce_account_id
            unique_accounts = []
            seen_ids = set()
            for account in found_accounts:
                account_id = account.get('salesforce_account_id')
                if account_id and account_id not in seen_ids:
                    unique_accounts.append(account)
                    seen_ids.add(account_id)
            
            if not unique_accounts:
                logger.info(f"ℹ️ No existing Salesforce accounts found to delete for folder: {dropbox_folder_name}")
                return True  # Return True since there's nothing to delete
            
            # Now try to delete each unique account
            for account in unique_accounts:
                account_id = account.get('salesforce_account_id')
                account_name = account.get('account_name', '')
                account_type = account.get('account_type', '')
                
                try:
                    # First, try to delete any related records (household members, etc.)
                    self._delete_related_records(account_id)
                    
                    # Then delete the account itself
                    delete_response = self.client.table('salesforce_accounts').delete().eq('salesforce_account_id', account_id).execute()
                    
                    if delete_response.data:
                        deleted_count += 1
                        logger.info(f"✅ Deleted Salesforce account: {account_name} (ID: {account_id})")
                    else:
                        logger.warning(f"⚠️ Failed to delete Salesforce account: {account_name} (ID: {account_id})")
                        
                except Exception as e:
                    error_msg = str(e)
                    if '409 Conflict' in error_msg and account_type == 'Household':
                        # Household accounts often can't be deleted due to constraints
                        logger.info(f"ℹ️ Cannot delete Household account '{account_name}' due to database constraints - this is expected behavior")
                        # Consider this a successful "deletion" since we can't delete it anyway
                        deleted_count += 1
                    else:
                        logger.warning(f"⚠️ Error deleting Salesforce account '{account_name}' (ID: {account_id}): {e}")
                    # Continue with other accounts even if one fails
                    continue
            
            logger.info(f"Processed {deleted_count} out of {len(unique_accounts)} Salesforce accounts for folder: {dropbox_folder_name}")
            return deleted_count > 0 or len(unique_accounts) == 0  # Return True if we processed some or found none to process
            
        except Exception as e:
            logger.error(f"Error deleting Salesforce accounts by folder name: {str(e)}")
            return False
    
    def _delete_related_records(self, account_id: str) -> None:
        """Delete related records before deleting the main account"""
        try:
            # Delete household members that reference this account
            try:
                self.client.table('salesforce_household_members').delete().eq('member_id', account_id).execute()
                logger.debug(f"Deleted household members for account: {account_id}")
            except Exception as e:
                logger.debug(f"No household members to delete for account {account_id}: {e}")
            
            # Delete household members that reference this account as household
            try:
                self.client.table('salesforce_household_members').delete().eq('household_id', account_id).execute()
                logger.debug(f"Deleted household members where account {account_id} is household")
            except Exception as e:
                logger.debug(f"No household members to delete where account {account_id} is household: {e}")
                
        except Exception as e:
            logger.warning(f"Error deleting related records for account {account_id}: {e}")
            # Don't raise the exception - we want to continue with the main deletion

    def search_salesforce_account_information(self, dropbox_account_folder_name: str) -> Optional[Dict[str, Any]]:
        """
        Search for Salesforce account information based on Dropbox account folder name.
        
        Args:
            dropbox_account_folder_name: The Dropbox account folder name to search for
            
        Returns:
            Dict containing structured Salesforce account information or None if not found
        """
        try:
            # Generate name variations for searching
            name_variations = [
                dropbox_account_folder_name,
                dropbox_account_folder_name.replace(', ', ' '),  # "Montesino, Maria" -> "Montesino Maria"
            ]
            
            # Add swapped name if it contains a comma
            if ', ' in dropbox_account_folder_name:
                parts = dropbox_account_folder_name.split(', ')
                if len(parts) == 2:
                    swapped_name = f"{parts[1]} {parts[0]}"  # "Montesino, Maria" -> "Maria Montesino"
                    name_variations.append(swapped_name)
            
            # Remove duplicates and None values
            name_variations = list(set([name for name in name_variations if name]))
            
            logger.info(f"Searching for Salesforce accounts with name variations: {name_variations}")
            
            # Search for exact matches first
            salesforce_accounts = []
            for name_var in name_variations:
                try:
                    # Search for exact matches
                    sf_result = self.client.table('salesforce_accounts').select('*').eq('account_name', name_var).execute()
                    if sf_result.data:
                        salesforce_accounts.extend(sf_result.data)
                        logger.info(f"Found {len(sf_result.data)} exact match(es) for '{name_var}'")
                    
                    # Search for partial matches (case-insensitive)
                    all_sf_result = self.client.table('salesforce_accounts').select('*').execute()
                    if all_sf_result.data:
                        for sf_acc in all_sf_result.data:
                            if name_var.lower() in sf_acc.get('account_name', '').lower():
                                if sf_acc not in salesforce_accounts:
                                    salesforce_accounts.append(sf_acc)
                                    logger.info(f"Found partial match: '{sf_acc.get('account_name')}' for '{name_var}'")
                                    
                except Exception as e:
                    logger.warning(f"Error searching for '{name_var}': {e}")
                    continue
            
            # Remove duplicates based on salesforce_account_id
            unique_accounts = []
            seen_ids = set()
            for account in salesforce_accounts:
                account_id = account.get('salesforce_account_id')
                if account_id and account_id not in seen_ids:
                    unique_accounts.append(account)
                    seen_ids.add(account_id)
            
            if not unique_accounts:
                logger.info(f"No Salesforce accounts found for Dropbox folder: {dropbox_account_folder_name}")
                return None
            
            logger.info(f"Found {len(unique_accounts)} unique Salesforce accounts for: {dropbox_account_folder_name}")
            
            # Structure the data similar to the salesforce_account_information format
            structured_data = {
                'names_found': [acc.get('account_name', '') for acc in unique_accounts],
                'household': None,
                'head': None,
                'members': [],
                'accounts': [],
                'not_found_accounts': []
            }
            
            # Process each account
            for account in unique_accounts:
                account_data = {
                    'account_name': account.get('account_name', ''),
                    'type': account.get('account_type', 'Contact'),
                    'role': account.get('role', None),
                    'stage': account.get('stage', ''),
                    'email': account.get('email', ''),
                    'phone': account.get('phone', ''),
                    'mailing_address': account.get('address', ''),
                    'ssn/tax_id': account.get('ssn_tax_id', ''),
                    'relationships': []
                }
                
                # Categorize accounts
                if account.get('account_type') == 'Household':
                    structured_data['household'] = account_data
                elif account.get('role') == 'Household Head':
                    structured_data['head'] = account_data
                elif account.get('role') == 'Member':
                    structured_data['members'].append(account_data)
                
                # Add to accounts list
                structured_data['accounts'].append(account_data)
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error searching for Salesforce account information for '{dropbox_account_folder_name}': {e}")
            return None

    def store_client_list_data_only(self, folder_name: str, client_list_info: DropboxAccountClientListInfo, 
                                   force: bool = False, update_existing: bool = True) -> Optional[int]:
        """Store only client list data for a dropbox account.
        
        This is a convenience method that creates a DropboxAccountWithFiles object with only
        client list data and no application files, then stores it using store_dropbox_account_with_files.
        
        Args:
            folder_name: The folder name for the account
            client_list_info: The client list information
            force: If True, delete existing account and re-insert (overwrites all data)
            update_existing: If True, update existing account fields instead of only inserting new ones
            
        Returns:
            The account ID if successful, None otherwise
        """
        logger.info(f"Store in Database: Storing client list data only for account: {folder_name}")
        
        # Create DropboxAccountWithFiles object with only client list data
        account = self.create_dropbox_account_with_files_from_client_list(
            folder_name=folder_name,
            client_list_info=client_list_info,
            application_files=[]  # No application files
        )
        
        # Store using the main method
        return self.store_dropbox_account_with_files(
            account=account,
            force=force,
            update_existing=update_existing
        )

    def create_dropbox_account_with_files_from_client_list(self, folder_name: str, client_list_info: DropboxAccountClientListInfo, 
                                                          application_files: List[DropboxAccountApplicationFile] = None) -> DropboxAccountWithFiles:
        """Create a DropboxAccountWithFiles object from client list data.
        
        Args:
            folder_name: The folder name for the account
            client_list_info: The client list information
            application_files: Optional list of application files (defaults to empty list)
            
        Returns:
            DropboxAccountWithFiles object ready for storage
        """
        if application_files is None:
            application_files = []
            
        # Create the account object
        account = DropboxAccountWithFiles(
            folder=folder_name,
            first_name=client_list_info.first_name,
            middle_name=client_list_info.middle_name,
            last_name=client_list_info.last_name,
            application_files=application_files,
            client_list_info=client_list_info,
            total_account_application_files=len(application_files),
            processed_account_application_files=len([f for f in application_files if f.status == ApplicationStatus.PROCESSED]),
            failed_account_application_files=len([f for f in application_files if f.status in [ApplicationStatus.FAILED, ApplicationStatus.ERROR]]),
            processing_timestamp=datetime.now()
        )
        
        return account

    def create_dropbox_account_client_list_info_from_dropbox_account_search_result(self, dropbox_account_search_result: Dict[str, Any]) -> DropboxAccountClientListInfo:
        """Create a DropboxAccountClientListInfo object from dropbox account search results.
        
        Args:
            dropbox_account_search_result: The result from dropbox_search_account containing account data
            
        Returns:
            DropboxAccountClientListInfo object ready for storage
        """
        from sync.utils.date_utils import convert_date
        
        # Extract account data
        account_data = dropbox_account_search_result.get('account_data', {})
        search_info = dropbox_account_search_result.get('search_info', {})
        match_info = search_info.get('match_info', {})
        drivers_license = dropbox_account_search_result.get('drivers_license', {})
        
        # Convert birthdate string to date if available
        birthdate = convert_date(account_data.get('birthdate'))
        
        # Create client list info object
        client_list_info = DropboxAccountClientListInfo(
            account_name=account_data.get('name', ''),
            first_name=account_data.get('first_name', ''),
            middle_name=account_data.get('middle_name', ''),
            last_name=account_data.get('last_name', ''),
            birthdate=birthdate,
            gender=account_data.get('gender', ''),
            phone=account_data.get('phone', ''),
            address=account_data.get('address', ''),
            city=account_data.get('city', ''),
            state=account_data.get('state', ''),
            zip_code=account_data.get('zip', ''),
            email=account_data.get('email', ''),
            additional_info=account_data.get('additional_info', ''),
            match_status=match_info.get('match_status', ''),
            drivers_license_data=drivers_license,
            search_info=search_info
        )
        
        return client_list_info

    def store_dropbox_client_list_data_from_search_result(self, dropbox_account_search_result: Dict[str, Any], 
                                                         folder_name: str, force: bool = False, 
                                                         update_existing: bool = True) -> Optional[int]:
        """Store dropbox client list data from search results in one step.
        
        This is a convenience method that creates a DropboxAccountClientListInfo object from search results
        and stores it using store_client_list_data_only.
        
        Args:
            dropbox_account_search_result: The result from dropbox_search_account containing account data
            folder_name: The folder name for the account
            force: If True, delete existing account and re-insert (overwrites all data)
            update_existing: If True, update existing account fields instead of only inserting new ones
            
        Returns:
            The account ID if successful, None otherwise
        """
        logger.info(f"Store in Database: Storing dropbox client list data from search result for account: {folder_name}")
        
        # Create client list info object from search result
        client_list_info = self.create_dropbox_account_client_list_info_from_dropbox_account_search_result(
            dropbox_account_search_result
        )
        
        # Store using the existing method
        return self.store_client_list_data_only(
            folder_name=folder_name,
            client_list_info=client_list_info,
            force=force,
            update_existing=update_existing
        )

    def store_dropbox_account_best_info(self, best_info: DropboxAccountBestInfo, dropbox_account_id: int, dropbox_account_folder_name: str = None) -> Optional[int]:
        """Store the best available account information from all Dropbox sources.
        
        Args:
            best_info: The DropboxAccountBestInfo object containing merged data
            dropbox_account_id: The ID of the dropbox account
            dropbox_account_folder_name: Optional folder name for logging
            
        Returns:
            The best info ID if successful, None otherwise
        """
        folder_name = dropbox_account_folder_name or f"account_id_{dropbox_account_id}"
        logger.info(f"Store in Database: dropbox best account info for account: {folder_name}, dropbox_account_id: {dropbox_account_id}")
        
        try:
            # First, delete any existing best info for this account to avoid duplicates
            logger.info(f"Deleting existing best info for account ID: {dropbox_account_id}")
            delete_response = self.client.table('dropbox_account_best_info').delete().eq('dropbox_account_id', dropbox_account_id).execute()
            logger.info(f"Deleted {len(delete_response.data) if delete_response.data else 0} existing records")
            
            # Prepare best info data
            best_info_data = {
                'dropbox_account_id': dropbox_account_id,
                'account_name': best_info.account_name,
                'first_name': best_info.first_name,
                'middle_name': best_info.middle_name,
                'last_name': best_info.last_name,
                'birthdate': best_info.birthdate.isoformat() if best_info.birthdate else None,
                'gender': best_info.gender,
                'phone': best_info.phone,
                'address': best_info.address,
                'city': best_info.city,
                'state': best_info.state,
                'zip_code': best_info.zip_code,
                'email': best_info.email,
                'additional_info': best_info.additional_info,
                'ssn_tax_id': best_info.ssn_tax_id,
                'data_sources': best_info.data_sources,
                'field_precedence': best_info.field_precedence,
                'confidence_score': best_info.confidence_score
            }
            
            best_info_data = self._serialize_dates(best_info_data)
            logger.info(f"Inserting best info: {best_info_data}")
            
            # Insert into the database
            response = self.client.table('dropbox_account_best_info').insert(best_info_data).execute()
            
            if response.data and len(response.data) > 0:
                best_info_id = response.data[0]['id']
                logger.info(f"Successfully stored best info with ID: {best_info_id}")
                return best_info_id
            else:
                # If no data returned but no error, try to query for the newly created record
                logger.warning("No data returned from best info insert, querying for new record...")
                query_response = self.client.table('dropbox_account_best_info').select('id').eq('dropbox_account_id', dropbox_account_id).limit(1).execute()
                
                if query_response.data and len(query_response.data) > 0:
                    best_info_id = query_response.data[0]['id']
                    logger.info(f"Found newly created best info with ID: {best_info_id}")
                    return best_info_id
                else:
                    logger.error("Failed to find newly created best info record")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to store best info for account ID: {dropbox_account_id}. Error: {e}")
            return None 

    def calculate_and_store_best_account_info(self, dropbox_account_id: int, folder_name: str) -> Optional[int]:
        """Calculate the best account information from all available sources and store it.
        
        This method merges data from both client list and application files sources
        to create the most complete and accurate account information.
        
        Args:
            dropbox_account_id: The ID of the dropbox account
            folder_name: The folder name for the account
            
        Returns:
            The best info ID if successful, None otherwise
        """
        logger.info(f"Calculating and storing best account info for account: {folder_name}, ID: {dropbox_account_id}")
        
        try:
            # Get client list info
            client_list_info = self.get_client_list_info_by_folder(folder_name)
            
            # Get application files info
            app_files_info = self.get_application_files_by_folder(folder_name)
            
            # Create best info object
            best_info = DropboxAccountBestInfo()
            best_info.account_name = folder_name
            
            # Track which sources contributed data
            data_sources = {}
            field_precedence = {}
            
            # Merge data from client list (preferred source)
            if client_list_info:
                logger.info(f"Found client list info for {folder_name}")
                data_sources['client_list'] = True
                
                # Copy client list data to best info
                best_info.first_name = client_list_info.first_name
                best_info.middle_name = client_list_info.middle_name
                best_info.last_name = client_list_info.last_name
                best_info.birthdate = client_list_info.birthdate
                best_info.gender = client_list_info.gender
                best_info.phone = client_list_info.phone
                best_info.address = client_list_info.address
                best_info.city = client_list_info.city
                best_info.state = client_list_info.state
                best_info.zip_code = client_list_info.zip_code
                best_info.email = client_list_info.email
                best_info.additional_info = client_list_info.additional_info
                
                # Mark fields as coming from client list
                for field in ['first_name', 'middle_name', 'last_name', 'birthdate', 'gender', 
                             'phone', 'address', 'city', 'state', 'zip_code', 'email', 'additional_info']:
                    if getattr(client_list_info, field):
                        field_precedence[field] = 'client_list'
            else:
                data_sources['client_list'] = False
            
            # Merge data from application files (fallback source)
            if app_files_info and app_files_info.application_files:
                logger.info(f"Found application files info for {folder_name}")
                data_sources['application_files'] = True
                
                # Get the best available info from application files
                best_app_file = None
                best_completeness = 0
                
                for app_file in app_files_info.application_files:
                    # Calculate completeness score for this file
                    completeness = 0
                    if app_file.owner.first_name or app_file.owner.last_name:
                        completeness += 2
                    if app_file.owner.date_of_birth:
                        completeness += 1
                    if app_file.owner.phone_number:
                        completeness += 1
                    if app_file.owner.email_address:
                        completeness += 1
                    if app_file.owner.mailing_address_street:
                        completeness += 1
                    
                    if completeness > best_completeness:
                        best_completeness = completeness
                        best_app_file = app_file
                
                # Use application files data for fields not already filled by client list
                if best_app_file and best_app_file.owner:
                    owner = best_app_file.owner
                    
                    if not best_info.first_name and owner.first_name:
                        best_info.first_name = owner.first_name
                        field_precedence['first_name'] = 'application_files'
                    
                    if not best_info.last_name and owner.last_name:
                        best_info.last_name = owner.last_name
                        field_precedence['last_name'] = 'application_files'
                    
                    if not best_info.birthdate and owner.date_of_birth:
                        best_info.birthdate = owner.date_of_birth
                        field_precedence['birthdate'] = 'application_files'
                    
                    if not best_info.phone and owner.phone_number:
                        best_info.phone = owner.phone_number
                        field_precedence['phone'] = 'application_files'
                    
                    if not best_info.email and owner.email_address:
                        best_info.email = owner.email_address
                        field_precedence['email'] = 'application_files'
                    
                    if not best_info.address and owner.mailing_address_street:
                        best_info.address = owner.mailing_address_street
                        field_precedence['address'] = 'application_files'
                    
                    if not best_info.city and owner.mailing_address_city:
                        best_info.city = owner.mailing_address_city
                        field_precedence['city'] = 'application_files'
                    
                    if not best_info.state and owner.mailing_address_state:
                        best_info.state = owner.mailing_address_state
                        field_precedence['state'] = 'application_files'
                    
                    if not best_info.zip_code and owner.mailing_address_zip:
                        best_info.zip_code = owner.mailing_address_zip
                        field_precedence['zip_code'] = 'application_files'
            else:
                data_sources['application_files'] = False
            
            # Calculate confidence score based on data completeness
            filled_fields = sum(1 for field in ['first_name', 'last_name', 'birthdate', 'phone', 'email', 'address'] 
                              if getattr(best_info, field))
            confidence_score = min(1.0, filled_fields / 6.0)  # Max 6 fields, score 0-1
            
            best_info.data_sources = data_sources
            best_info.field_precedence = field_precedence
            best_info.confidence_score = confidence_score
            
            logger.info(f"Calculated best info for {folder_name}: confidence={confidence_score}, sources={data_sources}")
            
            # Store the best info
            return self.store_dropbox_account_best_info(best_info, dropbox_account_id, folder_name)
            
        except Exception as e:
            logger.error(f"Failed to calculate and store best account info for {folder_name}. Error: {e}")
            return None