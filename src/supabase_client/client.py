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

    def store_application(self, application: Application) -> int:
        """Store an application in the database"""
        if not self._client:
            raise RuntimeError("Supabase client not initialized")
        data = application.model_dump()
        data = self._serialize_dates(data)
        result = self._client.table('applications').insert(data).execute()
        if not result.data:
            raise RuntimeError("Failed to create application")
        return result.data[0]['id']

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
        members_result = self._client.table("dropbox_account_household_members").select("id").eq("dropbox_account_id", account_id).execute()
        household_members = []
        for member in members_result.data:
            member_result = self._client.table("household_members").select("*").eq("id", member["id"]).execute()
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

    def get_dropbox_account_by_folder(self, folder_name: str) -> Optional[DropboxAccount]:
        """Retrieve a dropbox account by folder name"""
        if not self._client:
            raise RuntimeError("Supabase client not initialized")

        # Get account
        result = self._client.table("dropbox_accounts").select("*").eq("folder", folder_name).execute()
        if not result.data:
            return None

        account_data = result.data[0]

        # Get household head
        household_head = None
        if account_data.get("household_head_id"):
            head_result = self._client.table("household_members").select("*").eq("id", account_data["household_head_id"]).execute()
            if head_result.data:
                household_head = HouseholdMember(**head_result.data[0])

        # Get applications directly from applications table
        apps_result = self._client.table("applications").select("*").eq("dropbox_account_id", account_data["id"]).execute()
        applications = []
        if apps_result.data:
            for app_data in apps_result.data:
                applications.append(Application(**app_data))

        # Get household members
        members_result = self._client.table("household_members").select("id").eq("dropbox_account_id", account_data["id"]).execute()
        household_members = []
        for member in members_result.data:
            member_result = self._client.table("household_members").select("*").eq("id", member["id"]).execute()
            if member_result.data:
                household_members.append(HouseholdMember(**member_result.data[0]))

        return DropboxAccount(
            folder=account_data["folder"],
            first_name=account_data.get("first_name"),
            middle_name=account_data.get("middle_name"),
            last_name=account_data.get("last_name"),
            applications=applications,
            household_head=household_head,
            household_members=household_members
        )

    def generate_account_summary(self, folder_name: str) -> str:
        """Generate a summary for a specific Dropbox account.
        
        Args:
            folder_name: The name of the Dropbox folder to generate a summary for
            
        Returns:
            str: A formatted summary of the account's data
        """
        if not self._client:
            raise RuntimeError("Supabase client not initialized")

        summary_lines = []
        summary_lines.append(f"\nAccount Summary for: {folder_name}")
        summary_lines.append("=" * (len(folder_name) + 20))

        try:
            # Get the account with its applications
            result = self._client.table('dropbox_accounts').select('*, applications(*)').eq('folder', folder_name).execute()
            if not result.data:
                summary_lines.append(f"❌ No account found for folder: {folder_name}")
                return "\n".join(summary_lines)

            account = result.data[0]
            apps = account.get('applications', [])
            
            # Add account details
            summary_lines.append(f"\nAccount Details:")
            summary_lines.append(f"  Name: {account.get('first_name', '')} {account.get('middle_name', '')} {account.get('last_name', '')}".strip())
            
            # Add applications summary
            summary_lines.append(f"\nApplications ({len(apps)}):")
            if not apps:
                summary_lines.append(f"  🚫 No application files found")
            else:
                for app in apps:
                    # Format date as MM/DD/YYYY
                    birthdate = app.get('birthdate')
                    if birthdate:
                        try:
                            from datetime import datetime
                            dob = datetime.fromisoformat(birthdate)
                            dob_str = dob.strftime('%m/%d/%Y')
                        except (ValueError, TypeError):
                            dob_str = birthdate
                    else:
                        dob_str = 'N/A'
                    
                    # Get gender emoji
                    gender_emoji = '👩' if app.get('gender') == 'Female' else '👨' if app.get('gender') == 'Male' else ''
                    gender_str = app.get('gender', 'Unknown')
                    summary_lines.append(f"  ✅ {app['file_name']}")
                    summary_lines.append(f"    🎂 DOB: {dob_str}")
                    summary_lines.append(f"    ☑️ Gender: {gender_emoji} {gender_str}")
                    if app.get('address'):
                        summary_lines.append(f"    📍 Address: {app['address']}")

            # Get household members
            members_result = self._client.table('household_members').select('*').eq('dropbox_account_id', account['id']).execute()
            members = members_result.data if members_result.data else []
            
            # Add household members summary
            summary_lines.append(f"\nHousehold Members ({len(members)}):")
            if not members:
                summary_lines.append("  ❌ No household members found")
            else:
                for member in members:
                    is_head = "👑 " if member.get('is_household_head') else ""
                    name = f"{member.get('first_name', '')} {member.get('middle_name', '')} {member.get('last_name', '')}".strip()
                    dob = member.get('date_of_birth', 'N/A')
                    if dob and hasattr(dob, 'strftime'):
                        dob = dob.strftime('%m/%d/%Y')
                    gender_emoji = '👩' if member.get('gender') == 'Female' else '👨' if member.get('gender') == 'Male' else ''
                    summary_lines.append(f"  {is_head}{name}")
                    summary_lines.append(f"    🎂 DOB: {dob}")
                    summary_lines.append(f"    ☑️ Gender: {gender_emoji} {member.get('gender', 'Unknown')}")

            return "\n".join(summary_lines)

        except Exception as e:
            logger.error(f"Error generating account summary: {str(e)}")
            summary_lines.append(f"\n❌ Error generating summary: {str(e)}")
            return "\n".join(summary_lines)

    def generate_search_results_summary(self, folder_name: str, search_criteria: dict = None) -> str:
        """Display search results for a Dropbox account in a formatted way.
        
        Args:
            folder_name: The name of the Dropbox folder to search
            search_criteria: Optional dictionary containing search criteria (birthdate, gender, application_type)
            
        Returns:
            str: A formatted string containing the search results
        """
        if not self._client:
            raise RuntimeError("Supabase client not initialized")

        logger.debug("Generating search results summary for folder: %s", folder_name)
        logger.debug("Search criteria: %s", search_criteria)

        summary_lines = []
        summary_lines.append(f"\n📁 Dropbox Account Folder: {folder_name}")
        summary_lines.append("=" * (len(folder_name) + 30))

        try:
            # Get the account with its applications
            logger.debug("Querying Supabase for account: %s", folder_name)
            result = self._client.table('dropbox_accounts').select('*, applications(*)').eq('folder', folder_name).execute()
            
            if not result.data:
                logger.warning("No account found for folder: %s", folder_name)
                summary_lines.append(f"❌ No account found for folder: {folder_name}")
                return "\n".join(summary_lines)

            account = result.data[0]
            apps = account.get('applications', [])
            logger.debug("Found %d applications for account", len(apps))
            
            # Filter applications based on search criteria if provided
            if search_criteria:
                logger.debug("Filtering applications with criteria: %s", search_criteria)
                filtered_apps = []
                for app in apps:
                    matches = True
                    if search_criteria.get('birthdate'):
                        app_dob = app.get('birthdate', '')
                        logger.debug("Comparing birthdate: %s with %s", app_dob, search_criteria['birthdate'])
                        if search_criteria['birthdate'] not in str(app_dob):
                            matches = False
                    if search_criteria.get('gender'):
                        app_gender = app.get('gender', '').lower()
                        search_gender = search_criteria['gender'].lower()
                        logger.debug("Comparing gender: %s with %s", app_gender, search_gender)
                        if search_gender != app_gender:
                            matches = False
                    if search_criteria.get('application_type'):
                        app_type = app.get('application_type', '').lower()
                        search_type = search_criteria['application_type'].lower()
                        logger.debug("Comparing application type: %s with %s", app_type, search_type)
                        if search_type != app_type:
                            matches = False
                    if matches:
                        filtered_apps.append(app)
                apps = filtered_apps
                logger.debug("After filtering, found %d matching applications", len(apps))
            
            # Add applications summary
            summary_lines.append(f"\n✅ Applications ({len(apps)}):")
            if not apps:
                summary_lines.append(f"  🚫 No application files found")
            else:
                for app in apps:
                    # Format date as MM/DD/YYYY
                    birthdate = app.get('birthdate')
                    if birthdate:
                        try:
                            from datetime import datetime
                            dob = datetime.fromisoformat(birthdate)
                            dob_str = dob.strftime('%m/%d/%Y')
                            logger.debug("Formatted birthdate %s to %s", birthdate, dob_str)
                        except (ValueError, TypeError) as e:
                            logger.warning("Error formatting birthdate %s: %s", birthdate, str(e))
                            dob_str = birthdate
                    else:
                        dob_str = 'N/A'
                    
                    # Get gender emoji
                    gender_emoji = '👩' if app.get('gender') == 'Female' else '👨' if app.get('gender') == 'Male' else ''
                    gender_str = app.get('gender', 'Unknown')
                    logger.debug("Formatted gender %s with emoji %s", gender_str, gender_emoji)
                    
                    summary_lines.append(f"  ✅ {app['file_name']}")
                    summary_lines.append(f"    🎂 DOB: {dob_str}")
                    summary_lines.append(f"    ☑️ Gender: {gender_emoji} {gender_str}")
                    if app.get('address'):
                        summary_lines.append(f"    📍 Address: {app['address']}")
                    if app.get('application_type'):
                        summary_lines.append(f"    📄 Type: {app['application_type']}")
                    if app.get('status'):
                        summary_lines.append(f"    📊 Status: {app['status']}")

            return "\n".join(summary_lines)

        except Exception as e:
            import traceback
            error_msg = f"Error displaying search results: {str(e)}"
            stack_trace = traceback.format_exc()
            logger.error(error_msg)
            logger.error("Stack trace:\n%s", stack_trace)
            summary_lines.append(f"\n❌ Error displaying results: {str(e)}")
            summary_lines.append(f"\nStack trace:\n{stack_trace}")
            return "\n".join(summary_lines) 