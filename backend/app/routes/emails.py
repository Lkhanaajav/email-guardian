"""
Email routes for fetching, filtering, and managing emails.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models import User, Email, EmailThread, DailyDigest, UrgencyLevel, EmailCategory
from app.schemas import (
    EmailResponse, EmailListResponse, EmailFilters,
    DailyDigestResponse, DigestRequest, SyncResponse, SyncStatus,
    ChatRequest, ChatResponse, MessageResponse
)
from app.routes.auth import get_current_user
from app.services.scheduler import scheduler_service
from app.services.summarizer import SummarizerService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/emails", tags=["Emails"])
settings = get_settings()


@router.get("", response_model=EmailListResponse)
async def list_emails(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    urgency: Optional[str] = None,
    is_read: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
    sender: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List emails with optional filters and pagination.
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **category**: Filter by category (work, personal, finance, etc.)
    - **urgency**: Filter by urgency (urgent, normal, low)
    - **is_read**: Filter by read status
    - **start_date**: Filter emails after this date
    - **end_date**: Filter emails before this date
    - **search**: Search in subject and body
    - **sender**: Filter by sender email
    """
    # Build query
    query = select(Email).where(Email.user_id == current_user.id)
    
    # Apply filters
    if category:
        try:
            cat_enum = EmailCategory(category.lower())
            query = query.where(Email.category == cat_enum)
        except ValueError:
            pass
    
    if urgency:
        try:
            urg_enum = UrgencyLevel(urgency.lower())
            query = query.where(Email.urgency == urg_enum)
        except ValueError:
            pass
    
    if is_read is not None:
        query = query.where(Email.is_read == is_read)
    
    if start_date:
        query = query.where(Email.received_at >= start_date)
    
    if end_date:
        query = query.where(Email.received_at <= end_date)
    
    if sender:
        query = query.where(Email.sender_email.ilike(f"%{sender}%"))
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Email.subject.ilike(search_pattern),
                Email.body_preview.ilike(search_pattern),
                Email.summary.ilike(search_pattern),
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and ordering
    offset = (page - 1) * page_size
    query = query.order_by(Email.received_at.desc()).offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    emails = result.scalars().all()
    
    return EmailListResponse(
        emails=[EmailResponse.model_validate(e) for e in emails],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(emails)) < total,
    )


@router.get("/urgent", response_model=List[EmailResponse])
async def get_urgent_emails(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get urgent emails from the last 24 hours."""
    yesterday = datetime.utcnow() - timedelta(hours=24)
    
    result = await db.execute(
        select(Email)
        .where(
            Email.user_id == current_user.id,
            Email.urgency == UrgencyLevel.URGENT,
            Email.received_at >= yesterday,
        )
        .order_by(Email.received_at.desc())
        .limit(limit)
    )
    emails = result.scalars().all()
    
    return [EmailResponse.model_validate(e) for e in emails]


@router.get("/today", response_model=List[EmailResponse])
async def get_todays_emails(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all emails from today."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    result = await db.execute(
        select(Email)
        .where(
            Email.user_id == current_user.id,
            Email.received_at >= today_start,
        )
        .order_by(Email.received_at.desc())
    )
    emails = result.scalars().all()
    
    return [EmailResponse.model_validate(e) for e in emails]


@router.get("/digest", response_model=DailyDigestResponse)
async def get_daily_digest(
    date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get daily digest for a specific date.
    Defaults to yesterday if no date provided.
    """
    if date is None:
        date = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)
    else:
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    result = await db.execute(
        select(DailyDigest).where(
            DailyDigest.user_id == current_user.id,
            DailyDigest.digest_date == date,
        )
    )
    digest = result.scalar_one_or_none()
    
    if not digest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No digest found for {date.strftime('%Y-%m-%d')}",
        )
    
    return DailyDigestResponse.model_validate(digest)


@router.post("/digest/generate", response_model=DailyDigestResponse)
async def generate_digest(
    request: DigestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a digest for a custom date range.
    """
    start_date = request.start_date or (
        datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        - timedelta(days=1)
    )
    end_date = request.end_date or (start_date + timedelta(days=1))
    
    # Get emails for the range
    result = await db.execute(
        select(Email).where(
            Email.user_id == current_user.id,
            Email.received_at >= start_date,
            Email.received_at < end_date,
            Email.is_processed == True,
        ).order_by(Email.received_at.desc())
    )
    emails = result.scalars().all()
    
    if not emails:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No processed emails found for the specified date range",
        )
    
    # Generate digest
    summarizer = SummarizerService()
    email_data = [
        {
            "sender": e.sender,
            "subject": e.subject,
            "summary": e.summary,
            "action_items": e.action_items or [],
            "urgency": e.urgency.value if e.urgency else "normal",
            "category": e.category.value if e.category else "other",
        }
        for e in emails
    ]
    
    digest_content = await summarizer.generate_digest(email_data)
    
    # Check if digest already exists
    result = await db.execute(
        select(DailyDigest).where(
            DailyDigest.user_id == current_user.id,
            DailyDigest.digest_date == start_date,
        )
    )
    digest = result.scalar_one_or_none()
    
    if digest:
        # Update existing
        digest.email_count = len(emails)
        digest.overall_summary = digest_content.get("overall_summary")
        digest.top_emails = digest_content.get("top_emails")
        digest.all_action_items = digest_content.get("all_action_items")
        digest.patterns = digest_content.get("patterns")
    else:
        # Create new
        digest = DailyDigest(
            user_id=current_user.id,
            digest_date=start_date,
            email_count=len(emails),
            overall_summary=digest_content.get("overall_summary"),
            top_emails=digest_content.get("top_emails"),
            all_action_items=digest_content.get("all_action_items"),
            patterns=digest_content.get("patterns"),
        )
        db.add(digest)
    
    await db.commit()
    await db.refresh(digest)
    
    return DailyDigestResponse.model_validate(digest)


@router.get("/{email_id}", response_model=EmailResponse)
async def get_email(
    email_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single email by ID with full details."""
    result = await db.execute(
        select(Email).where(
            Email.id == email_id,
            Email.user_id == current_user.id,
        )
    )
    email = result.scalar_one_or_none()
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    return EmailResponse.model_validate(email)


@router.put("/{email_id}/read", response_model=EmailResponse)
async def mark_email_read(
    email_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark an email as read."""
    result = await db.execute(
        select(Email).where(
            Email.id == email_id,
            Email.user_id == current_user.id,
        )
    )
    email = result.scalar_one_or_none()
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    email.is_read = True
    email.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(email)
    
    return EmailResponse.model_validate(email)


@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(
    current_user: User = Depends(get_current_user),
):
    """Manually trigger email sync."""
    result = await scheduler_service.trigger_manual_sync(current_user.id)
    return SyncResponse(**result)


@router.get("/sync/status", response_model=SyncStatus)
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current sync status."""
    # Count emails
    result = await db.execute(
        select(func.count()).select_from(Email).where(
            Email.user_id == current_user.id
        )
    )
    total_emails = result.scalar()
    
    result = await db.execute(
        select(func.count()).select_from(Email).where(
            Email.user_id == current_user.id,
            Email.is_processed == True,
        )
    )
    processed_emails = result.scalar()
    
    return SyncStatus(
        is_syncing=False,  # Would need to track this in scheduler
        last_sync=current_user.last_sync,
        emails_synced=total_emails,
        emails_processed=processed_emails,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_emails(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Natural language query interface for emails.
    Ask questions like "Show me emails about project deadlines"
    """
    # Get recent emails for context
    result = await db.execute(
        select(Email)
        .where(
            Email.user_id == current_user.id,
            Email.is_processed == True,
        )
        .order_by(Email.received_at.desc())
        .limit(50)  # Limit context window
    )
    emails = result.scalars().all()
    
    if not emails:
        return ChatResponse(
            answer="You don't have any processed emails yet. Try syncing your inbox first.",
            relevant_emails=[],
        )
    
    # Prepare email data for query
    email_data = [
        {
            "sender": e.sender,
            "subject": e.subject,
            "summary": e.summary,
            "snippet": e.snippet,
            "received_at": e.received_at.isoformat() if e.received_at else None,
            "category": e.category.value if e.category else "other",
            "urgency": e.urgency.value if e.urgency else "normal",
        }
        for e in emails
    ]
    
    # Query using Claude
    summarizer = SummarizerService()
    
    # Convert conversation history
    history = None
    if request.conversation_history:
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]
    
    answer = await summarizer.query_emails(
        query=request.query,
        emails=email_data,
        conversation_history=history,
    )
    
    # Find relevant emails to return (simple keyword matching)
    query_lower = request.query.lower()
    relevant = []
    for email in emails[:10]:
        subject = (email.subject or "").lower()
        summary = (email.summary or "").lower()
        if any(word in subject or word in summary 
               for word in query_lower.split() if len(word) > 3):
            relevant.append(EmailResponse.model_validate(email))
    
    return ChatResponse(
        answer=answer,
        relevant_emails=relevant[:5],
    )
