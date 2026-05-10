"""
SQLAlchemy database models for EmailGuardian.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    Enum, ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class UrgencyLevel(str, enum.Enum):
    """Email urgency levels."""
    URGENT = "urgent"
    NORMAL = "normal"
    LOW = "low"


class EmailCategory(str, enum.Enum):
    """Email categories for classification."""
    WORK = "work"
    PERSONAL = "personal"
    FINANCE = "finance"
    NEWSLETTER = "newsletter"
    SHOPPING = "shopping"
    OTHER = "other"


class User(Base):
    """User model for storing Gmail account information."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    picture = Column(String(500), nullable=True)
    
    # OAuth tokens (encrypted in production)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    
    # Settings
    last_sync = Column(DateTime, nullable=True)
    notification_enabled = Column(Boolean, default=True)
    digest_enabled = Column(Boolean, default=True)
    digest_time = Column(String(5), default="08:00")  # HH:MM format
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    emails = relationship("Email", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email}>"


class EmailThread(Base):
    """Email thread model for grouping related emails."""
    
    __tablename__ = "email_threads"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    subject = Column(String(500), nullable=True)
    participant_count = Column(Integer, default=1)
    message_count = Column(Integer, default=1)
    
    # Thread-level summary (generated from all emails in thread)
    thread_summary = Column(Text, nullable=True)
    
    # Timestamps
    first_message_at = Column(DateTime, nullable=True)
    last_message_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    emails = relationship("Email", back_populates="thread", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<EmailThread {self.thread_id}>"


class Email(Base):
    """Email model for storing processed emails."""
    
    __tablename__ = "emails"
    
    id = Column(Integer, primary_key=True, index=True)
    gmail_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    thread_id = Column(Integer, ForeignKey("email_threads.id"), nullable=True)
    
    # Email metadata
    sender = Column(String(500), nullable=False)
    sender_email = Column(String(255), nullable=True, index=True)
    recipients = Column(JSON, nullable=True)  # List of recipient emails
    subject = Column(String(1000), nullable=True)
    snippet = Column(Text, nullable=True)  # Gmail's snippet
    body_preview = Column(Text, nullable=True)  # First 500 chars
    body_html = Column(Text, nullable=True)  # Full HTML body (optional)
    body_text = Column(Text, nullable=True)  # Plain text body
    
    # Gmail labels
    labels = Column(JSON, nullable=True)  # List of Gmail labels
    
    # AI-generated content
    summary = Column(Text, nullable=True)
    key_points = Column(JSON, nullable=True)  # List of bullet points
    action_items = Column(JSON, nullable=True)  # List of action items
    urgency = Column(Enum(UrgencyLevel), default=UrgencyLevel.NORMAL, index=True)
    category = Column(Enum(EmailCategory), default=EmailCategory.OTHER, index=True)
    
    # Processing status
    is_processed = Column(Boolean, default=False, index=True)
    is_read = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    
    # Timestamps
    received_at = Column(DateTime, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="emails")
    thread = relationship("EmailThread", back_populates="emails")
    
    # Indexes for common queries
    __table_args__ = (
        Index("ix_email_user_received", "user_id", "received_at"),
        Index("ix_email_user_urgency", "user_id", "urgency"),
        Index("ix_email_user_category", "user_id", "category"),
    )
    
    def __repr__(self):
        return f"<Email {self.gmail_id}: {self.subject[:50] if self.subject else 'No Subject'}>"


class DailyDigest(Base):
    """Daily digest model for storing generated digests."""
    
    __tablename__ = "daily_digests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    digest_date = Column(DateTime, nullable=False, index=True)
    email_count = Column(Integer, default=0)
    
    # Digest content
    overall_summary = Column(Text, nullable=True)
    top_emails = Column(JSON, nullable=True)  # List of top email summaries
    all_action_items = Column(JSON, nullable=True)  # Combined action items
    patterns = Column(Text, nullable=True)  # Notable patterns/trends
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Unique constraint on user + date
    __table_args__ = (
        Index("ix_digest_user_date", "user_id", "digest_date", unique=True),
    )
    
    def __repr__(self):
        return f"<DailyDigest {self.digest_date} for user {self.user_id}>"
