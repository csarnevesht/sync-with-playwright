#!/usr/bin/env python3
"""
Minimal test script to store a single Dropbox folder in Supabase and trigger granular logging.
"""

import os
import sys
import logging
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from supabase_client.client import SupabaseClient
from sync.dropbox_client.utils.app_file_extractor import DropboxAccountWithFiles, DropboxAccountApplicationFile, DropboxAccountApplicationInfo
from supabase_client.schema import ApplicationType, ApplicationStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    folder = "Cortes Jesse Daughters Betty & Gina"
    logger.info(f"Testing store_dropbox_account_with_files for folder: {folder}")

    # Create a minimal DropboxAccountWithFiles object
    test_app_file = DropboxAccountApplicationFile(
        file_name="test_file.pdf",
        file_path="/test/path/test_file.pdf",
        application_type=ApplicationType.ANNUITY,
        status=ApplicationStatus.PROCESSED,
        owner=DropboxAccountApplicationInfo(
            first_name="Test",
            last_name="User",
            date_of_birth=datetime(1990, 1, 1).date(),
            gender="M"
        ),
        joint_owner=DropboxAccountApplicationInfo(),
        notes=["Test file"],
        extracted_text="Test extracted text",
        ocr_confidence=0.95,
        lm_studio_model_used="test-model",
        processing_duration_seconds=1.0
    )
    test_account = DropboxAccountWithFiles(
        folder=folder,
        first_name="Test",
        last_name="User",
        application_files=[test_app_file],
        total_account_application_files=1,
        processed_account_application_files=1,
        failed_account_application_files=0,
        processing_timestamp=datetime.now()
    )

    supabase_client = SupabaseClient()
    account_id = supabase_client.store_dropbox_account_with_files(test_account, force=False, update_existing=True)
    if account_id:
        print(f"✅ store_dropbox_account_with_files returned account ID: {account_id}")
    else:
        print(f"❌ store_dropbox_account_with_files returned None (see logs for details)")

if __name__ == "__main__":
    main() 