from typing import Optional, date
from pydantic import BaseModel

class Application(BaseModel):
    """Model for an application."""
    file_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birthdate: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    application_type: str = "Insurance"
    status: str = "Pending"
    dropbox_account_id: Optional[int] = None
    
    model_config = {
        'json_encoders': {
            date: lambda v: v.isoformat() if v else None
        }
    } 