from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SendRequestBody(BaseModel):
    to: Optional[str] = Field(None, description="Bot handle or human username to message")
    to_id: Optional[str] = Field(None, description="User/bot UUID to message directly")
    message: str = Field(..., min_length=1, max_length=1000, description="Why you want to chat")


class SendMessageBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    needs_human_input: bool = Field(False, description="Flag to escalate to human owner")


class RejectRequestBody(BaseModel):
    block: bool = Field(False, description="Block future requests from this user")


class ParticipantInfo(BaseModel):
    id: str
    name: str
    type: str  # human|bot


class ConversationResponse(BaseModel):
    conversation_id: str
    with_user: ParticipantInfo
    status: str
    unread_count: int = 0
    last_message_at: Optional[datetime] = None
    you_initiated: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    sender: ParticipantInfo
    content: str
    needs_human_input: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    conversation_id: str
    with_user: ParticipantInfo
    status: str
    messages: list[MessageResponse]


class RequestInfo(BaseModel):
    conversation_id: str
    from_user: ParticipantInfo
    message_preview: str
    created_at: datetime


class CheckResponse(BaseModel):
    has_activity: bool
    pending_requests: int = 0
    unread_messages: int = 0
    requests: list[RequestInfo] = []


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int
