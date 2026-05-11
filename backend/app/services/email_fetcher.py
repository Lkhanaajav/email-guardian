"""
Gmail API integration service for fetching emails.
Handles OAuth tokens and email retrieval.
"""

import asyncio
import base64
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from email.utils import parseaddr

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import get_settings
from app.models import User, Email, EmailThread

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailFetcherService:
    """Service for fetching emails from Gmail API."""

    SCOPES = settings.gmail_scopes

    def __init__(self, user: User):
        """Initialize with user credentials."""
        self.user = user
        self._service = None
        self._credentials = None

    async def _get_credentials(self) -> Optional[Credentials]:
        """Get valid credentials, refreshing if necessary."""
        if not self.user.refresh_token:
            logger.error(f"No refresh token for user {self.user.email}")
            return None

        creds = Credentials(
            token=self.user.access_token,
            refresh_token=self.user.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.gmail_client_id,
            client_secret=settings.gmail_client_secret,
            scopes=self.SCOPES,
        )

        # Refresh if expired (blocking HTTP call — run in thread)
        if creds.expired and creds.refresh_token:
            try:
                await asyncio.to_thread(creds.refresh, Request())
                self.user.access_token = creds.token
                self.user.token_expiry = creds.expiry
                logger.info(f"Refreshed token for user {self.user.email}")
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                return None

        return creds

    async def _get_service(self):
        """Get Gmail API service instance."""
        if self._service is None:
            creds = await self._get_credentials()
            if creds:
                self._service = await asyncio.to_thread(
                    build, "gmail", "v1", credentials=creds
                )
        return self._service

    async def fetch_emails(
        self,
        since: Optional[datetime] = None,
        max_results: int = 100,
        exclude_labels: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails from Gmail.

        Args:
            since: Fetch emails after this datetime
            max_results: Maximum number of emails to fetch
            exclude_labels: Labels to exclude (e.g., SPAM, PROMOTIONS)

        Returns:
            List of email dictionaries with parsed content
        """
        service = await self._get_service()
        if not service:
            logger.error("Could not get Gmail service")
            return []

        # Build query
        query_parts = []

        if since:
            epoch = int(since.timestamp())
            query_parts.append(f"after:{epoch}")

        if exclude_labels is None:
            exclude_labels = ["SPAM", "CATEGORY_PROMOTIONS"]

        for label in exclude_labels:
            query_parts.append(f"-label:{label}")

        query = " ".join(query_parts) if query_parts else None

        try:
            results = await asyncio.to_thread(
                lambda: service.users().messages().list(
                    userId="me",
                    q=query,
                    maxResults=max_results,
                    labelIds=["INBOX"]
                ).execute()
            )

            messages = results.get("messages", [])
            logger.info(f"Found {len(messages)} emails for user {self.user.email}")

            if not messages:
                return []

            emails = []
            for msg in messages:
                try:
                    email_data = await self._fetch_message_details(service, msg["id"])
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    logger.error(f"Error fetching message {msg['id']}: {e}")
                    continue

            return emails

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching emails: {e}")
            return []

    async def _fetch_message_details(
        self,
        service,
        message_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch and parse a single email message."""
        try:
            message = await asyncio.to_thread(
                lambda: service.users().messages().get(
                    userId="me",
                    id=message_id,
                    format="full"
                ).execute()
            )

            return self._parse_message(message)

        except HttpError as e:
            logger.error(f"Error fetching message {message_id}: {e}")
            return None

    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail message into structured format."""
        headers = message.get("payload", {}).get("headers", [])

        header_dict = {h["name"].lower(): h["value"] for h in headers}

        sender_raw = header_dict.get("from", "Unknown")
        sender_name, sender_email = parseaddr(sender_raw)

        to_raw = header_dict.get("to", "")
        recipients = [parseaddr(r.strip())[1] for r in to_raw.split(",") if r.strip()]

        date_str = header_dict.get("date", "")
        try:
            from email.utils import parsedate_to_datetime
            received_at = parsedate_to_datetime(date_str)
        except Exception:
            received_at = datetime.utcnow()

        body_text, body_html = self._extract_body(message.get("payload", {}))

        labels = message.get("labelIds", [])

        return {
            "gmail_id": message["id"],
            "thread_id": message.get("threadId"),
            "sender": sender_raw,
            "sender_email": sender_email or sender_raw,
            "sender_name": sender_name,
            "recipients": recipients,
            "subject": header_dict.get("subject", "(No Subject)"),
            "snippet": message.get("snippet", ""),
            "body_text": body_text,
            "body_html": body_html,
            "body_preview": (body_text[:500] if body_text else "")[:500],
            "labels": labels,
            "received_at": received_at,
            "is_read": "UNREAD" not in labels,
            "is_starred": "STARRED" in labels,
        }

    def _extract_body(self, payload: Dict[str, Any]) -> tuple[str, str]:
        """Extract plain text and HTML body from email payload."""
        body_text = ""
        body_html = ""

        def extract_part(part: Dict[str, Any]):
            nonlocal body_text, body_html

            mime_type = part.get("mimeType", "")
            body = part.get("body", {})
            data = body.get("data", "")

            if data:
                decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                if mime_type == "text/plain" and not body_text:
                    body_text = decoded
                elif mime_type == "text/html" and not body_html:
                    body_html = decoded

            for sub_part in part.get("parts", []):
                extract_part(sub_part)

        extract_part(payload)

        if not body_text and body_html:
            try:
                from html import unescape
                import re
                text = re.sub(r"<[^>]+>", " ", body_html)
                text = unescape(text)
                text = re.sub(r"\s+", " ", text).strip()
                body_text = text[:5000]
            except Exception:
                pass

        return body_text, body_html

    async def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """Fetch all messages in a thread."""
        service = await self._get_service()
        if not service:
            return []

        try:
            thread = await asyncio.to_thread(
                lambda: service.users().threads().get(
                    userId="me",
                    id=thread_id,
                    format="full"
                ).execute()
            )

            messages = []
            for msg in thread.get("messages", []):
                parsed = self._parse_message(msg)
                messages.append(parsed)

            return messages

        except HttpError as e:
            logger.error(f"Error fetching thread {thread_id}: {e}")
            return []

    async def mark_as_read(self, gmail_id: str) -> bool:
        """Mark an email as read in Gmail."""
        service = await self._get_service()
        if not service:
            return False

        try:
            await asyncio.to_thread(
                lambda: service.users().messages().modify(
                    userId="me",
                    id=gmail_id,
                    body={"removeLabelIds": ["UNREAD"]}
                ).execute()
            )
            return True
        except HttpError as e:
            logger.error(f"Error marking message as read: {e}")
            return False

    async def get_labels(self) -> List[Dict[str, str]]:
        """Get all Gmail labels."""
        service = await self._get_service()
        if not service:
            return []

        try:
            results = await asyncio.to_thread(
                lambda: service.users().labels().list(userId="me").execute()
            )
            return results.get("labels", [])
        except HttpError as e:
            logger.error(f"Error fetching labels: {e}")
            return []
