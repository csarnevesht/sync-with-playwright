#!/usr/bin/env python3
"""
Generate Schema Diagram Script

This script generates an updated HTML schema diagram for the database
without the legacy applications table.
"""

import os
import sys
from datetime import datetime

def generate_schema_diagram():
    """Generate the updated schema diagram HTML."""
    
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Supabase Database Schema Diagram</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .content {
            padding: 40px;
        }
        
        .schema-overview {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 30px;
            border-left: 5px solid #3498db;
        }
        
        .schema-overview h2 {
            color: #2c3e50;
            margin-top: 0;
        }
        
        .tables-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }
        
        .table-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            overflow: hidden;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .table-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.15);
        }
        
        .table-header {
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            color: white;
            padding: 20px;
            position: relative;
        }
        
        .table-header h3 {
            margin: 0;
            font-size: 1.3em;
            font-weight: 600;
        }
        
        .table-type {
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(255,255,255,0.2);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 500;
        }
        
        .table-body {
            padding: 20px;
        }
        
        .field {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        
        .field:last-child {
            border-bottom: none;
        }
        
        .field-name {
            font-weight: 600;
            color: #2c3e50;
        }
        
        .field-type {
            background: #e8f4fd;
            color: #2980b9;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.85em;
            font-weight: 500;
        }
        
        .field-constraints {
            font-size: 0.8em;
            color: #7f8c8d;
            margin-top: 4px;
        }
        
        .relationships {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 30px;
        }
        
        .relationships h2 {
            color: #2c3e50;
            margin-top: 0;
        }
        
        .relationship-item {
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #e74c3c;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .relationship-item h4 {
            margin: 0 0 10px 0;
            color: #2c3e50;
        }
        
        .relationship-desc {
            color: #7f8c8d;
            font-size: 0.9em;
            line-height: 1.5;
        }
        
        .enums-section {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 30px;
        }
        
        .enums-section h2 {
            color: #2c3e50;
            margin-top: 0;
        }
        
        .enum-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #f39c12;
        }
        
        .enum-card h4 {
            margin: 0 0 15px 0;
            color: #2c3e50;
        }
        
        .enum-values {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .enum-value {
            background: #fff3cd;
            color: #856404;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }
        
        .footer {
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Database Schema Diagram</h1>
            <p>Current database structure for Dropbox account data extraction and storage</p>
        </div>
        
        <div class="content">
            <div class="schema-overview">
                <h2>📊 Schema Overview</h2>
                <p>This database schema is designed to store and manage Dropbox account data, extracted application files, and person details extracted from insurance applications. The system supports comprehensive file processing with OCR capabilities and detailed person information tracking.</p>
            </div>
            
            <div class="tables-grid">
                <!-- Main Tables -->
                <div class="table-section">
                    <h2>Main Tables</h2>
                    <div class="table-grid">
                        <div class="table-card">
                            <h3>dropbox_accounts</h3>
                            <p>Core table storing Dropbox account information and folder metadata.</p>
                            <ul>
                                <li><strong>folder:</strong> Unique folder name from Dropbox</li>
                                <li><strong>first_name, last_name:</strong> Account holder information</li>
                                <li><strong>total_files, processed_files, failed_files:</strong> Processing statistics</li>
                                <li><strong>processing_timestamp:</strong> Last processing time</li>
                            </ul>
                        </div>
                        
                        <div class="table-card">
                            <h3>dropbox_account_application_info</h3>
                            <p>Stores person information (owners and joint owners) extracted from application files.</p>
                            <ul>
                                <li><strong>first_name, last_name:</strong> Person's name</li>
                                <li><strong>date_of_birth, gender:</strong> Personal details</li>
                                <li><strong>mailing_address_*:</strong> Complete address information</li>
                                <li><strong>phone_number, email_address:</strong> Contact information</li>
                                <li><strong>ocr_method:</strong> Method used for data extraction</li>
                            </ul>
                        </div>
                        
                        <div class="table-card">
                            <h3>dropbox_account_application_files</h3>
                            <p>Comprehensive file processing data and metadata for each application file.</p>
                            <ul>
                                <li><strong>file_name, file_path:</strong> File identification</li>
                                <li><strong>application_type:</strong> Type of insurance application</li>
                                <li><strong>status:</strong> Processing status (Processed/Failed/Error/Skipped)</li>
                                <li><strong>owner_id, joint_owner_id:</strong> Links to person information</li>
                                <li><strong>extracted_text:</strong> Raw text from file processing</li>
                                <li><strong>ocr_confidence:</strong> Confidence score from OCR</li>
                                <li><strong>lm_studio_model_used:</strong> AI model used for processing</li>
                                <li><strong>processing_duration_seconds:</strong> Processing time</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="relationships">
                <h2>🔗 Table Relationships</h2>
                
                <div class="relationship-item">
                    <h4>dropbox_accounts ↔ dropbox_account_application_files</h4>
                    <div class="relationship-desc">
                        <strong>One-to-Many:</strong> Each Dropbox account can have multiple application files. Files are linked via the <code>dropbox_account_id</code> foreign key.
                    </div>
                </div>
                
                <div class="relationship-item">
                    <h4>dropbox_account_application_info ↔ dropbox_account_application_files (Owner)</h4>
                    <div class="relationship-desc">
                        <strong>One-to-Many:</strong> Each person can be the owner of multiple application files. Files are linked via the <code>owner_id</code> foreign key.
                    </div>
                </div>
                
                <div class="relationship-item">
                    <h4>dropbox_account_application_info ↔ dropbox_account_application_files (Joint Owner)</h4>
                    <div class="relationship-desc">
                        <strong>One-to-Many:</strong> Each person can be the joint owner of multiple application files. Files are linked via the <code>joint_owner_id</code> foreign key.
                    </div>
                </div>
            </div>
            
            <div class="enums-section">
                <h2>📋 Enum Types</h2>
                
                <div class="enum-card">
                    <h4>application_status</h4>
                    <div class="enum-values">
                        <span class="enum-value">Processed</span>
                        <span class="enum-value">Failed</span>
                        <span class="enum-value">Error</span>
                        <span class="enum-value">Skipped</span>
                    </div>
                </div>
                
                <div class="enum-card">
                    <h4>application_type</h4>
                    <div class="enum-values">
                        <span class="enum-value">Life Insurance</span>
                        <span class="enum-value">Annuity</span>
                        <span class="enum-value">EquiTrust Annuity</span>
                        <span class="enum-value">Security Benefit</span>
                        <span class="enum-value">Unknown</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Schema diagram generated on ''' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ''' | Legacy tables removed</p>
        </div>
    </div>
</body>
</html>'''
    
    # Write the HTML file
    output_path = os.path.join(os.path.dirname(__file__), '..', 'diagrams', 'database_schema_diagram.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Schema diagram generated: {output_path}")

if __name__ == "__main__":
    generate_schema_diagram() 