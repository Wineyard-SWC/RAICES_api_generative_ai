from pydantic import BaseModel
from typing import Optional, List, Dict

from datetime import datetime

class RequestBody(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatMessage(BaseModel):
    message:str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    message: Dict
    session_id:str

class AddContentRequest(BaseModel):
    content: str
    source_name: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

class EpicRequestBody(BaseModel):
    requirements_description: Dict
    session_id: str

class StoryRequestBody(BaseModel):
    epic_description: Dict
    session_id: str