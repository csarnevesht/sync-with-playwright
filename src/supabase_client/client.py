import os
from typing import Optional, List
from supabase import create_client, Client as SupabaseBaseClient
from .schema import Application, DropboxAccount, HouseholdMember
from dotenv import load_dotenv
import logging
import jwt
import time
import collections.abc

logger = logging.getLogger(__name__)

class SupabaseClient:
    """
    Client for interacting with Supabase database
    """
    _instance = None
    _client: Optional[SupabaseBaseClient] = None

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

        # Get the Supabase URL
        supabase_url = os.getenv('SUPABASE_URL', 'http://localhost:8000')
        logger.debug(f"Using Supabase URL: {supabase_url}")

        # Get the Supabase service role key from the .env file
        service_role_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not service_role_key:
            raise ValueError("SUPABASE_SERVICE_KEY not set in .env file!")
        logger.debug(f"Using Supabase service role key: {service_role_key}")

        try:
            # Create the Supabase client with the service role key
            self._client = create_client(supabase_url, service_role_key)
            # Test the connection
            self._client.table('dropbox_accounts').select('count').execute()
            logger.info("Successfully connected to Supabase")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {str(e)}")
            raise

    @property
    def client(self) -> SupabaseBaseClient:
        """Get the Supabase client instance"""
        return self._client

    def store_application(self, application: Application) -> None:
        """Store an application in the database"""
        if not self._client:
            raise RuntimeError("Supabase client not initialized")
        data = application.model_dump()
        data = self._serialize_dates(data)
        self._client.table('applications').insert(data).execute()

    def store_household_member(self, member: HouseholdMember) -> None:
        """Store a household member in the database"""
        if not self._client:
            raise RuntimeError("Supabase client not initialized")
        data = member.model_dump()
        data = self._serialize_dates(data)
        self._client.table('household_members').insert(data).execute()

    def _serialize_dates(self, obj):
        if isinstance(obj, dict):
            return {k: self._serialize_dates(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_dates(i) for i in obj]
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            return obj

    def store_dropbox_account(self, account: DropboxAccount) -> None:
        """Store a Dropbox account and its related data"""
        if not self._client:
            raise RuntimeError("Supabase client not initialized")
        
        # Store the account
        account_data = account.model_dump(exclude={'applications', 'household_members', 'household_head'})
        if account.household_head:
            account_data['household_head_id'] = None
        account_data = self._serialize_dates(account_data)
        self._client.table('dropbox_accounts').insert(account_data).execute()
        
        # Store applications
        for application in account.applications:
            self.store_application(application)
        
        # Store household members
        for member in account.household_members:
            self.store_household_member(member)

    def get_dropbox_account(self, account_id: int) -> Optional[DropboxAccount]:
        """Retrieve a dropbox account by ID"""
        if not self._client:
            raise RuntimeError("Supabase client not initialized")

        # Get account
        result = self._client.table("dropbox_accounts").select("*").eq("id", account_id).execute()
        if not result.data:
            return None

        account_data = result.data[0]

        # Get household head
        household_head = None
        if account_data["household_head_id"]:
            head_result = self._client.table("household_members").select("*").eq("id", account_data["household_head_id"]).execute()
            if head_result.data:
                household_head = HouseholdMember(**head_result.data[0])

        # Get applications
        apps_result = self._client.table("dropbox_account_applications").select("application_id").eq("dropbox_account_id", account_id).execute()
        applications = []
        for app in apps_result.data:
            app_result = self._client.table("applications").select("*").eq("id", app["application_id"]).execute()
            if app_result.data:
                applications.append(Application(**app_result.data[0]))

        # Get household members
        members_result = self._client.table("dropbox_account_household_members").select("household_member_id").eq("dropbox_account_id", account_id).execute()
        household_members = []
        for member in members_result.data:
            member_result = self._client.table("household_members").select("*").eq("id", member["household_member_id"]).execute()
            if member_result.data:
                household_members.append(HouseholdMember(**member_result.data[0]))

        return DropboxAccount(
            folder=account_data["folder"],
            first_name=account_data["first_name"],
            middle_name=account_data["middle_name"],
            last_name=account_data["last_name"],
            applications=applications,
            household_head=household_head,
            household_members=household_members
        ) 