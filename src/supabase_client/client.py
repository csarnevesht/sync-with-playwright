import os
from typing import Optional, List, Dict, Any
from supabase import create_client, Client as SupabaseBaseClient
from .schema import (
    DropboxAccountWithFiles, ApplicationStatus, ApplicationType,
    DropboxAccountApplicationFile, DropboxAccountApplicationInfo, DropboxAccountClientListInfo
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
    
    def limit(self, count: int):
        self.params["limit"] = str(count)
        return self
    
    def execute(self):
        params = "&".join([f"{k}={v}" for k, v in self.params.items()])
        url = f"{self.endpoint}?select={self.columns}"
        if params:
            url += f"&{params}"
        
        with httpx.Client() as client:
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
        with httpx.Client() as client:
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
        with httpx.Client() as client:
            response = client.delete(url, headers=self.headers)
            response.raise_for_status()
            # Return a dummy response object for compatibility
            return type('Response', (), {'data': response.json() if response.text.strip() else []})()

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

    def store_application_file(self, app_file: DropboxAccountApplicationFile, dropbox_account_id: int) -> Optional[int]:
        """Store application file data and return the file ID"""
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
            print(f"[DEBUG] Inserting application file: {file_data}")
            # Insert into the database
            response = self.client.table('dropbox_account_application_files').insert(file_data).execute()
            print(f"[DEBUG] Insert response: {getattr(response, 'data', None)} | Error: {getattr(response, 'error', None)}")
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            else:
                logger.warning("No data returned from application_files insert")
                return None
        except Exception as e:
            logger.error(f"Error storing application file: {str(e)}")
            print(f"[ERROR] Exception in store_application_file: {e}")
            return None

    def store_dropbox_account_with_files(self, account: DropboxAccountWithFiles, force: bool = False) -> Optional[int]:
        """Store dropbox account and its application files. If account exists, use its ID, or delete and re-insert if force=True."""
        try:
            # First check if the account already exists
            existing_account_response = self.client.table('dropbox_accounts').select('id').eq('folder', account.folder).execute()
            account_id = None
            if existing_account_response.data and len(existing_account_response.data) > 0:
                account_id = existing_account_response.data[0]['id']
                print(f"[DEBUG] Existing account found for folder: {account.folder}, ID: {account_id}")
                if force:
                    print(f"[DEBUG] Force flag is set. Deleting account ID: {account_id} and all related files before re-inserting.")
                    self.delete_application_files_for_folder(account.folder)
                    self.client.table('dropbox_accounts').delete().eq('id', account_id).execute()
                    account_id = None
            else:
                print(f"[DEBUG] No existing account found for folder: {account.folder}")

            # Insert new account if needed
            if account_id is None:
                account_data = {
                    'folder': account.folder,
                    'first_name': account.first_name,
                    'middle_name': account.middle_name,
                    'last_name': account.last_name,
                    'total_files': account.total_files,
                    'processed_files': account.processed_files,
                    'failed_files': account.failed_files,
                    'processing_timestamp': account.processing_timestamp.isoformat() if account.processing_timestamp else None
                }
                account_data = self._serialize_dates(account_data)
                print(f"[DEBUG] Inserting dropbox account: {account_data}")
                response = self.client.table('dropbox_accounts').insert(account_data).execute()
                print(f"[DEBUG] Insert response: {getattr(response, 'data', None)} | Error: {getattr(response, 'error', None)}")
                if response.data and len(response.data) > 0:
                    account_id = response.data[0]['id']
                    print(f"[DEBUG] Created new account ID: {account_id}")
                else:
                    # Insert succeeded but no data returned (common with local Supabase)
                    # Query for the newly created record to get its ID
                    print(f"[DEBUG] Insert succeeded but no data returned, querying for new record...")
                    new_account_response = self.client.table('dropbox_accounts').select('id').eq('folder', account.folder).execute()
                    if new_account_response.data and len(new_account_response.data) > 0:
                        account_id = new_account_response.data[0]['id']
                        print(f"[DEBUG] Found newly created account ID: {account_id}")
                    else:
                        logger.error(f"Failed to insert dropbox account: Could not find newly created record")
                        return None
            else:
                print(f"[DEBUG] Using existing account ID: {account_id} for folder: {account.folder}")

            # Store client list info if available
            if account.client_list_info:
                print(f"[DEBUG] Storing client list info for account ID: {account_id}")
                self.store_client_list_info(account.client_list_info, account_id)

            # Store each application file
            for app_file in account.application_files:
                print(f"[DEBUG] Storing application file: {app_file.file_name} for account ID: {account_id}")
                print(f"[DEBUG] Application file data: {app_file}")
                self.store_application_file(app_file, account_id)
            return account_id
        except Exception as e:
            logger.error(f"Error storing dropbox account with files: {str(e)}")
            print(f"[ERROR] Exception in store_dropbox_account_with_files: {e}")
            return None

    def get_application_files_by_folder(self, folder_name: str) -> Optional[DropboxAccountWithFiles]:
        """Get all application files for a specific folder"""
        try:
            # First get the dropbox account
            account_response = self.client.table('dropbox_accounts').select('*').eq('folder', folder_name).execute()
            
            if not account_response.data or len(account_response.data) == 0:
                logger.warning(f"No dropbox account found for folder: {folder_name}")
                return None
            
            account_data = account_response.data[0]
            
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
                total_files=account_data.get('total_files', 0),
                processed_files=account_data.get('processed_files', 0),
                failed_files=account_data.get('failed_files', 0),
                processing_timestamp=datetime.fromisoformat(account_data['processing_timestamp']) if account_data.get('processing_timestamp') else None
            )
            
            return account
            
        except Exception as e:
            logger.error(f"Error getting application files by folder: {str(e)}")
            return None

    def check_application_file_exists(self, folder_name: str, file_name: str) -> bool:
        """Check if a specific application file already exists for a folder"""
        try:
            # Get the dropbox account
            account_response = self.client.table('dropbox_accounts').select('id').eq('folder', folder_name).execute()
            
            if not account_response.data or len(account_response.data) == 0:
                return False
            
            account_id = account_response.data[0]['id']
            
            # Check if the specific file exists
            files_response = self.client.table('dropbox_account_application_files').select('id').eq('dropbox_account_id', account_id).eq('file_name', file_name).execute()
            
            return len(files_response.data) > 0
            
        except Exception as e:
            logger.error(f"Error checking application file exists: {str(e)}")
            return False

    def check_application_files_exist(self, folder_name: str) -> bool:
        """Check if application files exist for a folder"""
        try:
            # Get the dropbox account
            account_response = self.client.table('dropbox_accounts').select('id').eq('folder', folder_name).execute()
            
            if not account_response.data or len(account_response.data) == 0:
                return False
            
            account_id = account_response.data[0]['id']
            
            # Check if there are any application files
            files_response = self.client.table('dropbox_account_application_files').select('id').eq('dropbox_account_id', account_id).execute()
            
            return len(files_response.data) > 0
            
        except Exception as e:
            logger.error(f"Error checking application files exist: {str(e)}")
            return False

    def delete_application_files_for_folder(self, folder_name: str) -> bool:
        """Delete all application files for a specific folder"""
        try:
            # Get the dropbox account
            account_response = self.client.table('dropbox_accounts').select('id').eq('folder', folder_name).execute()
            
            if not account_response.data or len(account_response.data) == 0:
                logger.warning(f"No dropbox account found for folder: {folder_name}")
                return False
            
            account_id = account_response.data[0]['id']
            
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
            summary_lines.append(f"   • Total Files: {account.total_files}")
            summary_lines.append(f"   • Processed: {account.processed_files}")
            summary_lines.append(f"   • Failed: {account.failed_files}")
            
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

    def store_client_list_info(self, client_list_info: DropboxAccountClientListInfo, dropbox_account_id: int) -> Optional[int]:
        """Store client list file data and return the client list info ID"""
        try:
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
                return response.data[0]['id']
            else:
                logger.warning("No data returned from client_list_info insert")
                return None
        except Exception as e:
            logger.error(f"Error storing client list info: {str(e)}")
            print(f"[ERROR] Exception in store_client_list_info: {e}")
            return None

    def get_client_list_info_by_folder(self, folder_name: str) -> Optional[DropboxAccountClientListInfo]:
        """Get client list info for a specific folder"""
        try:
            # First get the dropbox account
            account_response = self.client.table('dropbox_accounts').select('id').eq('folder', folder_name).execute()
            
            if not account_response.data or len(account_response.data) == 0:
                logger.warning(f"No dropbox account found for folder: {folder_name}")
                return None
            
            account_id = account_response.data[0]['id']
            
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
            logger.error(f"Error getting client list info by folder: {str(e)}")
            return None

    def delete_client_list_info_for_folder(self, folder_name: str) -> bool:
        """Delete client list info for a specific folder"""
        try:
            # Get the dropbox account
            account_response = self.client.table('dropbox_accounts').select('id').eq('folder', folder_name).execute()
            
            if not account_response.data or len(account_response.data) == 0:
                logger.warning(f"No dropbox account found for folder: {folder_name}")
                return False
            
            account_id = account_response.data[0]['id']
            
            # Delete client list info
            self.client.table('dropbox_account_client_list_info').delete().eq('dropbox_account_id', account_id).execute()
            
            logger.info(f"Deleted client list info for folder: {folder_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting client list info for folder: {str(e)}")
            return False 