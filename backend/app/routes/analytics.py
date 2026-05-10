"""
Analytics routes for email statistics and insights.
"""

import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import User, Email, UrgencyLevel, EmailCategory
from app.schemas import (
    AnalyticsResponse, CategoryCount, UrgencyCount, SenderStats
)
from app.routes.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("", response_model=AnalyticsResponse)
async def get_analytics(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get email analytics and statistics.
    
    - **days**: Number of days to include in analysis (default: 7)
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    
    # Total emails
    result = await db.execute(
        select(func.count()).select_from(Email).where(
            Email.user_id == current_user.id,
            Email.received_at >= cutoff_date,
        )
    )
    total_emails = result.scalar() or 0
    
    # Unread count
    result = await db.execute(
        select(func.count()).select_from(Email).where(
            Email.user_id == current_user.id,
            Email.received_at >= cutoff_date,
            Email.is_read == False,
        )
    )
    unread_count = result.scalar() or 0
    
    # Processed count
    result = await db.execute(
        select(func.count()).select_from(Email).where(
            Email.user_id == current_user.id,
            Email.received_at >= cutoff_date,
            Email.is_processed == True,
        )
    )
    processed_count = result.scalar() or 0
    
    # Urgent count
    result = await db.execute(
        select(func.count()).select_from(Email).where(
            Email.user_id == current_user.id,
            Email.received_at >= cutoff_date,
            Email.urgency == UrgencyLevel.URGENT,
        )
    )
    urgent_count = result.scalar() or 0
    
    # Category breakdown
    category_results = await db.execute(
        select(Email.category, func.count().label("count"))
        .where(
            Email.user_id == current_user.id,
            Email.received_at >= cutoff_date,
        )
        .group_by(Email.category)
    )
    category_breakdown = [
        CategoryCount(category=row.category, count=row.count)
        for row in category_results
        if row.category is not None
    ]
    
    # Urgency breakdown
    urgency_results = await db.execute(
        select(Email.urgency, func.count().label("count"))
        .where(
            Email.user_id == current_user.id,
            Email.received_at >= cutoff_date,
        )
        .group_by(Email.urgency)
    )
    urgency_breakdown = [
        UrgencyCount(urgency=row.urgency, count=row.count)
        for row in urgency_results
        if row.urgency is not None
    ]
    
    # Top senders
    sender_results = await db.execute(
        select(
            Email.sender_email,
            Email.sender,
            func.count().label("count")
        )
        .where(
            Email.user_id == current_user.id,
            Email.received_at >= cutoff_date,
            Email.sender_email.isnot(None),
        )
        .group_by(Email.sender_email, Email.sender)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_senders = [
        SenderStats(
            sender_email=row.sender_email,
            sender_name=row.sender,
            email_count=row.count,
        )
        for row in sender_results
    ]
    
    # Emails today
    result = await db.execute(
        select(func.count()).select_from(Email).where(
            Email.user_id == current_user.id,
            Email.received_at >= today_start,
        )
    )
    emails_today = result.scalar() or 0
    
    # Emails this week
    result = await db.execute(
        select(func.count()).select_from(Email).where(
            Email.user_id == current_user.id,
            Email.received_at >= week_start,
        )
    )
    emails_this_week = result.scalar() or 0
    
    return AnalyticsResponse(
        total_emails=total_emails,
        unread_count=unread_count,
        processed_count=processed_count,
        urgent_count=urgent_count,
        category_breakdown=category_breakdown,
        urgency_breakdown=urgency_breakdown,
        top_senders=top_senders,
        emails_today=emails_today,
        emails_this_week=emails_this_week,
    )


@router.get("/trends")
async def get_email_trends(
    days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get email volume trends over time.
    Returns daily email counts for the specified period.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # This is a simplified version - in production you'd use date_trunc
    result = await db.execute(
        select(
            func.date(Email.received_at).label("date"),
            func.count().label("count"),
        )
        .where(
            Email.user_id == current_user.id,
            Email.received_at >= cutoff_date,
        )
        .group_by(func.date(Email.received_at))
        .order_by(func.date(Email.received_at))
    )
    
    trends = [
        {"date": str(row.date), "count": row.count}
        for row in result
    ]
    
    return {"trends": trends, "days": days}


@router.get("/action-items")
async def get_pending_action_items(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all pending action items from recent emails.
    """
    # Get emails with action items from the last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    result = await db.execute(
        select(Email)
        .where(
            Email.user_id == current_user.id,
            Email.received_at >= week_ago,
            Email.action_items.isnot(None),
        )
        .order_by(Email.received_at.desc())
        .limit(limit)
    )
    emails = result.scalars().all()
    
    # Compile action items with email context
    action_items = []
    for email in emails:
        if email.action_items:
            for item in email.action_items:
                action_items.append({
                    "action": item,
                    "from_email": {
                        "id": email.id,
                        "subject": email.subject,
                        "sender": email.sender,
                        "received_at": email.received_at.isoformat() if email.received_at else None,
                        "urgency": email.urgency.value if email.urgency else "normal",
                    }
                })
    
    return {
        "action_items": action_items,
        "total_count": len(action_items),
    }


@router.get("/category/{category}")
async def get_category_details(
    category: str,
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed analytics for a specific category.
    """
    try:
        cat_enum = EmailCategory(category.lower())
    except ValueError:
        return {"error": f"Invalid category: {category}"}
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get count
    result = await db.execute(
        select(func.count()).select_from(Email).where(
            Email.user_id == current_user.id,
            Email.category == cat_enum,
            Email.received_at >= cutoff_date,
        )
    )
    count = result.scalar() or 0
    
    # Get top senders for this category
    sender_results = await db.execute(
        select(
            Email.sender_email,
            func.count().label("count")
        )
        .where(
            Email.user_id == current_user.id,
            Email.category == cat_enum,
            Email.received_at >= cutoff_date,
        )
        .group_by(Email.sender_email)
        .order_by(func.count().desc())
        .limit(5)
    )
    top_senders = [
        {"sender": row.sender_email, "count": row.count}
        for row in sender_results
    ]
    
    # Get recent subjects
    result = await db.execute(
        select(Email.subject, Email.received_at)
        .where(
            Email.user_id == current_user.id,
            Email.category == cat_enum,
            Email.received_at >= cutoff_date,
        )
        .order_by(Email.received_at.desc())
        .limit(5)
    )
    recent = [
        {"subject": row.subject, "date": row.received_at.isoformat() if row.received_at else None}
        for row in result
    ]
    
    return {
        "category": category,
        "total_count": count,
        "top_senders": top_senders,
        "recent_subjects": recent,
        "period_days": days,
    }
