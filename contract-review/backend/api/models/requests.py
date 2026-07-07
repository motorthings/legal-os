"""
Request models for API endpoints
All Pydantic models for validating incoming requests
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal


class ConversationCreateRequest(BaseModel):
    user_id: str
    title: str = Field(default="New Conversation", max_length=200)
    client_id: Optional[str] = None

    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()


class ConversationRenameRequest(BaseModel):
    title: str = Field(max_length=200, min_length=1)

    @validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()


class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    role: Optional[Literal['admin', 'user']] = None


class UserCreateRequest(BaseModel):
    email: str = Field(max_length=255)
    name: str = Field(max_length=100)
    password: str = Field(min_length=8)
    role: Literal['admin', 'user'] = 'user'
    client_id: Optional[str] = None


class ClientCreateRequest(BaseModel):
    name: str = Field(max_length=200)
    assistant_name: str = Field(default="SuperAssistant", max_length=100)


class ClientUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None


class ChatRequest(BaseModel):
    conversation_id: str
    message: str = Field(min_length=1, max_length=10000)
    document_ids: Optional[list[str]] = None
    use_rag: Optional[bool] = True
