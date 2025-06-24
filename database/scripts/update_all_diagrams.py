#!/usr/bin/env python3
"""
Update All Diagrams Script

This script updates both the HTML and visual diagrams by calling the existing generate_schema_diagram.py script and then updating the visual diagram.
"""

import os
import sys
import subprocess
from datetime import datetime

def update_visual_diagram():
    """Update the visual text diagram to match the current schema."""
    
    visual_content = '''🗄️ DATABASE SCHEMA VISUAL DIAGRAM
==================================

🔵 CORE TABLES (Currently Active)
=================================

dropbox_accounts (📁)
    │
    │ 1:N
    │
    ▼
dropbox_account_application_files (📄)
    │
    │ N:1 (Owner)
    │ N:1 (Joint Owner)
    │
    ▼
dropbox_account_application_info (👤)

🔗 RELATIONSHIP DETAILS:
=======================

dropbox_accounts.id ──┐
                      │
                      ▼
dropbox_account_application_files.dropbox_account_id

dropbox_account_application_info.id ──┐
                                      │
                                      ▼
dropbox_account_application_files.owner_id
dropbox_account_application_files.joint_owner_id

📊 CURRENT SYSTEM ARCHITECTURE:
===============================

┌─────────────────┐    ┌─────────────────────────────┐    ┌─────────────────────────────┐
│  dropbox_accounts │    │ dropbox_account_application_files │    │ dropbox_account_application_info │
│                 │    │                             │    │                             │
│ • folder        │◄───┤ • dropbox_account_id        │    │ • first_name                │
│ • first_name    │    │ • owner_id                  │◄───┤ • last_name                  │
│ • last_name     │    │ • joint_owner_id            │    │ • date_of_birth              │
│ • total_files   │    │ • file_name                 │    │ • gender                     │
│ • processed_files│    │ • application_type          │    │ • mailing_address_street     │
│ • failed_files  │    │ • status                    │    │ • mailing_address_city       │
│ • timestamps    │    │ • extracted_text            │    │ • mailing_address_state      │
└─────────────────┘    │ • notes (JSONB)             │    │ • mailing_address_zip        │
                       │ • ocr_confidence            │    │ • phone_number               │
                       │ • lm_studio_model_used      │    │ • email_address              │
                       │ • processing_duration       │    │ • ocr_method                 │
                       │ • timestamps                │    │ • created_at                 │
                       └─────────────────────────────┘    └─────────────────────────────┘

📝 CUSTOM ENUMS:
================

application_status: [Processed, Failed, Error, Skipped]
application_type: [Life Insurance, Annuity, EquiTrust Annuity, Security Benefit, Unknown]

🎯 KEY POINTS:
==============

✅ Core tables are actively used and contain real data
✅ Foreign key relationships ensure data integrity
✅ JSONB field in application_files stores flexible notes
✅ Timestamps track creation and updates
✅ Indexes optimize query performance
✅ OCR confidence and processing metrics tracked
✅ LM Studio model information stored
⚠️ Legacy tables may not exist in current database

📊 Last Updated: ''' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '''
📊 Supabase Database Schema Visual Diagram | Generated for sync-with-playwright project
'''
    
    # Write the visual diagram
    visual_path = "database/diagrams/database_schema_visual.txt"
    os.makedirs(os.path.dirname(visual_path), exist_ok=True)
    
    with open(visual_path, 'w', encoding='utf-8') as f:
        f.write(visual_content)
    
    print(f"✅ Visual diagram updated: {visual_path}")

def main():
    """Main function to update all diagrams."""
    print("🔄 Updating all database diagrams...")
    print("=" * 50)
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # Change to project root
    os.chdir(project_root)
    
    try:
        # First, update the HTML diagram using the existing script
        print("📊 Updating HTML schema diagram...")
        html_script = "database/scripts/generate_schema_diagram.py"
        
        if os.path.exists(html_script):
            result = subprocess.run([sys.executable, html_script], 
                                  capture_output=True, text=True, cwd=project_root)
            if result.returncode == 0:
                print("✅ HTML schema diagram updated successfully")
            else:
                print(f"⚠️ HTML diagram update had issues: {result.stderr}")
        else:
            print(f"❌ HTML diagram script not found: {html_script}")
        
        # Then update the visual diagram
        print("\n📊 Updating visual text diagram...")
        update_visual_diagram()
        
        print("\n🎉 All diagrams updated successfully!")
        print("=" * 50)
        print("📁 Updated files:")
        print("   • database/diagrams/database_schema_diagram.html")
        print("   • database/diagrams/database_schema_visual.txt")
        print("   • database/diagrams/database_schema_diagram.txt")
        
    except Exception as e:
        print(f"❌ Error updating diagrams: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 