"""
Background task scheduler using APScheduler.
Handles periodic email fetching, processing, and digest generation.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import async_session_maker
from app.models import User, Email, EmailThread, DailyDigest, UrgencyLevel, EmailCategory
from app.services.email_fetcher import EmailFetcherService
from app.services.summarizer import SummarizerService
from app.services.classifier import ClassifierService

logger = logging.getLogger(__name__)
settings = get_settings()


class SchedulerService:
    """Service for managing background tasks."""
    
    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.summarizer = SummarizerService()
        self.classifier = ClassifierService()
        self._is_running = False
    
    def start(self):
        """Start the scheduler with all jobs."""
        if self._is_running:
            logger.warning("Scheduler is already running")
            return
        
        # Add email fetch job - every 15 minutes
        self.scheduler.add_job(
            self.fetch_and_process_all_users,
            trigger=IntervalTrigger(minutes=settings.fetch_interval_minutes),
            id="fetch_emails",
            name="Fetch and process emails for all users",
            replace_existing=True,
            max_instances=1,
        )
        
        # Add daily digest job - at configured hour
        self.scheduler.add_job(
            self.generate_daily_digests,
            trigger=CronTrigger(hour=settings.digest_hour, minute=0),
            id="daily_digest",
            name="Generate daily digests",
            replace_existing=True,
            max_instances=1,
        )
        
        # Add cleanup job - weekly on Sunday at 3 AM
        self.scheduler.add_job(
            self.cleanup_old_emails,
            trigger=CronTrigger(day_of_week="sun", hour=3, minute=0),
            id="cleanup",
            name="Cleanup old processed emails",
            replace_existing=True,
            max_instances=1,
        )
        
        self.scheduler.start()
        self._is_running = True
        logger.info("Scheduler started successfully")
    
    def stop(self):
        """Stop the scheduler."""
        if self._is_running:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Scheduler stopped")
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._is_running
    
    async def fetch_and_process_all_users(self):
        """Fetch and process emails for all users."""
        logger.info("Starting scheduled email fetch for all users")
        
        async with async_session_maker() as session:
            # Get all users with valid tokens
            result = await session.execute(
                select(User).where(User.refresh_token.isnot(None))
            )
            users = result.scalars().all()
            
            for user in users:
                try:
                    await self.fetch_and_process_user_emails(session, user)
                except Exception as e:
                    logger.error(f"Error processing emails for user {user.email}: {e}")
                    continue
            
            await session.commit()
        
        logger.info("Completed scheduled email fetch")
    
    async def fetch_and_process_user_emails(
        self, 
        session: AsyncSession, 
        user: User
    ) -> int:
        """
        Fetch and process emails for a single user.
        
        Args:
            session: Database session
            user: User to process emails for
        
        Returns:
            Number of new emails processed
        """
        logger.info(f"Fetching emails for user: {user.email}")
        
        # Determine fetch window
        since = user.last_sync
        if since is None:
            # First run: fetch last 24 hours
            since = datetime.utcnow() - timedelta(hours=24)
        
        # Fetch emails from Gmail
        fetcher = EmailFetcherService(user)
        raw_emails = await fetcher.fetch_emails(since=since)
        
        if not raw_emails:
            logger.info(f"No new emails for user {user.email}")
            user.last_sync = datetime.utcnow()
            return 0
        
        # Filter out already processed emails
        existing_gmail_ids = await self._get_existing_gmail_ids(session, user.id)
        new_emails = [e for e in raw_emails if e["gmail_id"] not in existing_gmail_ids]
        
        if not new_emails:
            logger.info(f"All emails already processed for user {user.email}")
            user.last_sync = datetime.utcnow()
            return 0
        
        logger.info(f"Processing {len(new_emails)} new emails for user {user.email}")
        
        # Process each email
        processed_count = 0
        for email_data in new_emails:
            try:
                await self._process_single_email(session, user, email_data)
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing email {email_data.get('gmail_id')}: {e}")
                continue
        
        # Update user's last sync time
        user.last_sync = datetime.utcnow()
        
        # Commit changes for this user
        await session.commit()
        
        logger.info(f"Processed {processed_count} emails for user {user.email}")
        return processed_count
    
    async def _get_existing_gmail_ids(
        self, 
        session: AsyncSession, 
        user_id: int
    ) -> set:
        """Get set of existing Gmail IDs for a user."""
        result = await session.execute(
            select(Email.gmail_id).where(Email.user_id == user_id)
        )
        return set(row[0] for row in result.fetchall())
    
    async def _process_single_email(
        self, 
        session: AsyncSession, 
        user: User,
        email_data: dict
    ):
        """Process a single email: classify, summarize, and store."""
        # Enrich with classification
        email_data = self.classifier.enrich_email(email_data)
        
        # Skip likely spam
        if email_data.get("is_likely_spam", False):
            logger.debug(f"Skipping likely spam: {email_data.get('subject')}")
            return
        
        # Get or create thread
        thread = await self._get_or_create_thread(
            session, user.id, email_data.get("thread_id")
        )
        
        # Generate AI summary
        try:
            summary = await self.summarizer.summarize_email(
                sender=email_data.get("sender", "Unknown"),
                subject=email_data.get("subject", ""),
                body=email_data.get("body_text", email_data.get("body_preview", "")),
                date=email_data.get("received_at")
            )
            
            # Use AI classification over rule-based if available
            urgency = summary.urgency
            category = summary.category
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            summary = None
            urgency = email_data.get("urgency", UrgencyLevel.NORMAL)
            category = email_data.get("category", EmailCategory.OTHER)
        
        # Create email record
        email = Email(
            gmail_id=email_data["gmail_id"],
            user_id=user.id,
            thread_id=thread.id if thread else None,
            sender=email_data.get("sender", "Unknown"),
            sender_email=email_data.get("sender_email"),
            recipients=email_data.get("recipients"),
            subject=email_data.get("subject"),
            snippet=email_data.get("snippet"),
            body_preview=email_data.get("body_preview"),
            body_text=email_data.get("body_text"),
            body_html=email_data.get("body_html"),
            labels=email_data.get("labels"),
            summary=summary.summary if summary else None,
            key_points=summary.key_points if summary else None,
            action_items=summary.action_items if summary else None,
            urgency=urgency,
            category=category,
            is_processed=summary is not None,
            is_read=email_data.get("is_read", False),
            is_starred=email_data.get("is_starred", False),
            received_at=email_data.get("received_at", datetime.utcnow()),
            processed_at=datetime.utcnow() if summary else None,
        )
        
        session.add(email)
        
        # Update thread stats
        if thread:
            thread.message_count += 1
            if email.received_at:
                if thread.first_message_at is None or email.received_at < thread.first_message_at:
                    thread.first_message_at = email.received_at
                if thread.last_message_at is None or email.received_at > thread.last_message_at:
                    thread.last_message_at = email.received_at
            if email.subject and not thread.subject:
                thread.subject = email.subject
    
    async def _get_or_create_thread(
        self, 
        session: AsyncSession, 
        user_id: int,
        gmail_thread_id: Optional[str]
    ) -> Optional[EmailThread]:
        """Get existing thread or create new one."""
        if not gmail_thread_id:
            return None
        
        result = await session.execute(
            select(EmailThread).where(
                EmailThread.thread_id == gmail_thread_id,
                EmailThread.user_id == user_id
            )
        )
        thread = result.scalar_one_or_none()
        
        if not thread:
            thread = EmailThread(
                thread_id=gmail_thread_id,
                user_id=user_id,
            )
            session.add(thread)
            await session.flush()
        
        return thread
    
    async def generate_daily_digests(self):
        """Generate daily digests for all users."""
        logger.info("Starting daily digest generation")
        
        async with async_session_maker() as session:
            # Get all users with digest enabled
            result = await session.execute(
                select(User).where(User.digest_enabled == True)
            )
            users = result.scalars().all()
            
            yesterday = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=1)
            today = yesterday + timedelta(days=1)
            
            for user in users:
                try:
                    await self._generate_user_digest(
                        session, user, yesterday, today
                    )
                except Exception as e:
                    logger.error(f"Error generating digest for user {user.email}: {e}")
                    continue
            
            await session.commit()
        
        logger.info("Completed daily digest generation")
    
    async def _generate_user_digest(
        self, 
        session: AsyncSession,
        user: User,
        start_date: datetime,
        end_date: datetime
    ):
        """Generate a digest for a single user."""
        # Check if digest already exists
        result = await session.execute(
            select(DailyDigest).where(
                DailyDigest.user_id == user.id,
                DailyDigest.digest_date == start_date
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.debug(f"Digest already exists for user {user.email} on {start_date}")
            return
        
        # Get emails from the date range
        result = await session.execute(
            select(Email).where(
                Email.user_id == user.id,
                Email.received_at >= start_date,
                Email.received_at < end_date,
                Email.is_processed == True
            ).order_by(Email.received_at.desc())
        )
        emails = result.scalars().all()
        
        if not emails:
            logger.info(f"No emails to digest for user {user.email}")
            return
        
        # Prepare email data for digest
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
        
        # Generate digest using AI
        digest_content = await self.summarizer.generate_digest(email_data)
        
        # Create digest record
        digest = DailyDigest(
            user_id=user.id,
            digest_date=start_date,
            email_count=len(emails),
            overall_summary=digest_content.get("overall_summary"),
            top_emails=digest_content.get("top_emails"),
            all_action_items=digest_content.get("all_action_items"),
            patterns=digest_content.get("patterns"),
        )
        
        session.add(digest)
        logger.info(f"Generated digest for user {user.email}: {len(emails)} emails")
    
    async def cleanup_old_emails(self, days_to_keep: int = 30):
        """Clean up old processed emails."""
        logger.info(f"Starting cleanup of emails older than {days_to_keep} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        async with async_session_maker() as session:
            # Delete old emails (keeping threads intact for now)
            from sqlalchemy import delete
            
            result = await session.execute(
                delete(Email).where(
                    Email.received_at < cutoff_date,
                    Email.is_starred == False  # Don't delete starred
                )
            )
            
            deleted_count = result.rowcount
            await session.commit()
            
            logger.info(f"Deleted {deleted_count} old emails")
    
    async def trigger_manual_sync(self, user_id: int) -> dict:
        """
        Manually trigger email sync for a user.
        
        Args:
            user_id: User ID to sync
        
        Returns:
            Dictionary with sync results
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {"success": False, "message": "User not found"}
            
            try:
                new_count = await self.fetch_and_process_user_emails(session, user)
                return {
                    "success": True,
                    "new_emails": new_count,
                    "message": f"Synced {new_count} new emails"
                }
            except Exception as e:
                logger.error(f"Manual sync failed: {e}")
                return {"success": False, "message": str(e)}
    
    def get_job_status(self) -> list:
        """Get status of all scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return jobs


# Global scheduler instance
scheduler_service = SchedulerService()
