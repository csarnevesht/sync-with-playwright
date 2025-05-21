import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import traceback
import sys

class OperationLogger:
    def __init__(self, log_file: str = "operations.log"):
        self.log_file = log_file
        self.operations = self._load_operations()
        
    def _load_operations(self) -> Dict:
        """Load existing operations from the log file."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {"accounts": [], "failed_steps": []}
        return {"accounts": [], "failed_steps": []}
    
    def _save_operations(self):
        """Save operations to the log file."""
        with open(self.log_file, 'w') as f:
            json.dump(self.operations, f, indent=2)
    
    def log_account_creation(self, account_name: str, account_id: str, files: List[str]):
        """Log a successful account creation."""
        account_entry = {
            "account_name": account_name,
            "account_id": account_id,
            "files": files,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        self.operations["accounts"].append(account_entry)
        self._save_operations()
    
    def log_file_upload(self, account_name: str, file_name: str, status: str):
        """Log a file upload operation."""
        # Find the account entry
        for account in self.operations["accounts"]:
            if account["account_name"] == account_name:
                if "file_uploads" not in account:
                    account["file_uploads"] = []
                account["file_uploads"].append({
                    "file_name": file_name,
                    "status": status,
                    "timestamp": datetime.now().isoformat()
                })
                self._save_operations()
                break
    
    def log_failed_step(self, step_type: str, details: Dict):
        """Log a failed operation step."""
        frame = sys._getframe(1)  # Get the caller's frame
        # Try to get the current exception's stack trace, else fallback to current stack
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_type is not None:
            stack_trace = traceback.format_exc()
        else:
            stack_trace = ''.join(traceback.format_stack())
        failed_step = {
            "step_type": step_type,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "status": "failed",
            "error_location": {
                "file": frame.f_code.co_filename,
                "line": frame.f_lineno
            },
            "stack_trace": stack_trace
        }
        self.operations["failed_steps"].append(failed_step)
        self._save_operations()
    
    def get_failed_steps(self) -> List[Dict]:
        """Get all failed steps."""
        return self.operations.get("failed_steps", [])
    
    def clear_failed_steps(self):
        """Clear all failed steps."""
        self.operations["failed_steps"] = []
        self._save_operations()
    
    def get_accounts(self) -> List[Dict]:
        """Get all processed accounts."""
        return self.operations.get("accounts", [])
    
    def get_account_by_name(self, account_name: str) -> Optional[Dict]:
        """Get account details by name."""
        for account in self.operations["accounts"]:
            if account["account_name"] == account_name:
                return account
        return None 