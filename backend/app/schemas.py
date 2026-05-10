"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


# Enums
class UrgencyLevel(str, Enum):
    URGENT = "urgent"
    NORMAL = "normal"
    LOW = "low"


class EmailCategory(str, Enum):
    WORK = "work"
    PERSONAL = "personal"
    FINANCE = "finance"
    NEWSLETTER = "newsletter"
    SHOPPING = "shopping"
    OTHER = "other"


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    picture: Optional[str] = None
    last_sync: Optional[datetime] = None
    notification_enabled: bool = True
    digest_enabled: bool = True
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserSettings(BaseModel):
    notification_enabled: Optional[bool] = None
    digest_enabled: Optional[bool] = None
    digest_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")


# Email schemas
class EmailBase(BaseModel):
    gmail_id: str
    sender: str
    sender_email: Optional[str] = None
    subject: Optional[str] = None
    snippet: Optional[str] = None
    received_at: datetime


class EmailSummary(BaseModel):
    """AI-generated email summary."""
    summary: str
    key_points: List[str] = []
    action_items: List[str] = []
    urgency: UrgencyLevel = UrgencyLevel.NORMAL
    category: EmailCategory = EmailCategory.OTHER


class EmailResponse(EmailBase):
    """Full email response with summary."""
    id: int
    body_preview: Optional[str] = None
    summary: Optional[str] = None
    key_points: Optional[List[str]] = None
    action_items: Optional[List[str]] = None
    urgency: UrgencyLevel = UrgencyLevel.NORMAL
    category: EmailCategory = EmailCategory.OTHER
    is_read: bool = False
    is_starred: bool = False
    is_processed: bool = False
    labels: Optional[List[str]] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class EmailListResponse(BaseModel):
    """Paginated email list response."""
    emails: List[EmailResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class EmailFilters(BaseModel):
    """Filters for email queries."""
    category: Optional[EmailCategory] = None
    urgency: Optional[UrgencyLevel] = None
    is_read: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search: Optional[str] = None
    sender: Optional[str] = None


# Thread schemas
class EmailThreadResponse(BaseModel):
    id: int
    thread_id: str
    subject: Optional[str] = None
    participant_count: int = 1
    message_count: int = 1
    thread_summary: Optional[str] = None
    first_message_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Digest schemas
class DailyDigestResponse(BaseModel):
    id: int
    digest_date: datetime
    email_count: int = 0
    overall_summary: Optional[str] = None
    top_emails: Optional[List[dict]] = None
    all_action_items: Optional[List[str]] = None
    patterns: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DigestRequest(BaseModel):
    """Request to generate a digest for a specific date range."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# Analytics schemas
class CategoryCount(BaseModel):
    category: EmailCategory
    count: int


class UrgencyCount(BaseModel):
    urgency: UrgencyLevel
    count: int


class SenderStats(BaseModel):
    sender_email: str
    sender_name: Optional[str] = None
    email_count: int


class AnalyticsResponse(BaseModel):
    total_emails: int
    unread_count: int
    processed_count: int
    urgent_count: int
    category_breakdown: List[CategoryCount]
    urgency_breakdown: List[UrgencyCount]
    top_senders: List[SenderStats]
    emails_today: int
    emails_this_week: int


# Chat schemas
class ChatMessage(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    """Request for natural language email query."""
    query: str = Field(..., min_length=1, max_length=1000)
    conversation_history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    """Response from chat interface."""
    answer: str
    relevant_emails: Optional[List[EmailResponse]] = None
    suggested_actions: Optional[List[str]] = None


# Auth schemas
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class OAuthCallbackResponse(BaseModel):
    success: bool
    user: Optional[UserResponse] = None
    access_token: Optional[str] = None
    message: Optional[str] = None


# Sync schemas
class SyncStatus(BaseModel):
    is_syncing: bool
    last_sync: Optional[datetime] = None
    emails_synced: int = 0
    emails_processed: int = 0


class SyncResponse(BaseModel):
    success: bool
    new_emails: int = 0
    processed_emails: int = 0
    message: Optional[str] = None


# Generic response
class MessageResponse(BaseModel):
    success: bool
    message: str
