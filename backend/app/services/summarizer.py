"""
Claude API integration for email summarization.
Uses Anthropic's Claude to generate summaries, key points, and action items.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import anthropic

from app.config import get_settings
from app.schemas import EmailSummary, UrgencyLevel, EmailCategory

logger = logging.getLogger(__name__)
settings = get_settings()


class SummarizerService:
    """Service for summarizing emails using Claude API."""
    
    EMAIL_SUMMARY_PROMPT = """Analyze this email and provide a structured summary.

Email Details:
From: {sender}
Subject: {subject}
Date: {date}

Body:
{body}

---

Provide your analysis in the following JSON format:
{{
    "summary": "A 2-3 sentence summary of the email's main content and purpose",
    "key_points": ["Key point 1", "Key point 2", ...],
    "action_items": ["Action item 1", "Action item 2", ...],
    "urgency": "urgent|normal|low",
    "category": "work|personal|finance|newsletter|shopping|other"
}}

Guidelines:
- Summary should capture the essential message in 2-3 sentences
- Key points should be max 5 bullet points highlighting important information
- Action items should list any tasks or responses required from the recipient
- Urgency levels:
  - "urgent": Requires immediate attention (deadlines, emergencies, time-sensitive)
  - "normal": Standard importance, can be addressed in regular workflow
  - "low": Informational, newsletters, no action required
- Categories:
  - "work": Professional emails, colleagues, business matters
  - "personal": Friends, family, personal matters
  - "finance": Banking, bills, financial services
  - "newsletter": Subscriptions, updates, marketing
  - "shopping": Orders, deliveries, retail
  - "other": Anything that doesn't fit above categories

Respond ONLY with the JSON object, no additional text."""

    DIGEST_PROMPT = """Create a concise daily digest from these email summaries:

{email_summaries}

---

Provide your digest in the following JSON format:
{{
    "overall_summary": "2-3 sentences summarizing the day's emails and their overall theme",
    "top_emails": [
        {{
            "subject": "Email subject",
            "sender": "Sender name",
            "why_important": "Brief explanation of importance"
        }}
    ],
    "all_action_items": ["Combined action item 1", "Action item 2", ...],
    "patterns": "Notable patterns or trends observed (e.g., 'Multiple emails about project X deadline')"
}}

Guidelines:
- Include only the top 3 most important emails
- Combine and deduplicate action items across all emails
- Keep everything brief and actionable
- Focus on what needs attention today

Respond ONLY with the JSON object, no additional text."""

    CHAT_QUERY_PROMPT = """You are an AI assistant helping a user search and understand their emails.

The user has asked: "{query}"

Here are the relevant emails from their inbox:

{email_context}

---

Based on these emails, provide a helpful response to the user's query. If asking about specific emails, reference them by subject and sender. If asking for summaries or patterns, synthesize the information.

Be concise, helpful, and accurate. If the information isn't available in the provided emails, say so clearly.

Respond in a natural, conversational tone."""

    def __init__(self):
        """Initialize the Anthropic client."""
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
    
    async def summarize_email(
        self, 
        sender: str,
        subject: str,
        body: str,
        date: Optional[datetime] = None
    ) -> EmailSummary:
        """
        Generate a summary for a single email.
        
        Args:
            sender: Email sender
            subject: Email subject
            body: Email body text
            date: Email received date
        
        Returns:
            EmailSummary with generated content
        """
        # Truncate body if too long (Claude has context limits)
        max_body_length = 8000
        truncated_body = body[:max_body_length] if body else ""
        if len(body) > max_body_length:
            truncated_body += "\n... [truncated]"
        
        prompt = self.EMAIL_SUMMARY_PROMPT.format(
            sender=sender,
            subject=subject or "(No Subject)",
            date=date.strftime("%Y-%m-%d %H:%M") if date else "Unknown",
            body=truncated_body or "(No body content)"
        )
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse response
            content = response.content[0].text
            result = json.loads(content)
            
            return EmailSummary(
                summary=result.get("summary", "Unable to generate summary"),
                key_points=result.get("key_points", [])[:5],
                action_items=result.get("action_items", []),
                urgency=self._parse_urgency(result.get("urgency", "normal")),
                category=self._parse_category(result.get("category", "other"))
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            return self._fallback_summary()
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            return self._fallback_summary()
        except Exception as e:
            logger.error(f"Unexpected error during summarization: {e}")
            return self._fallback_summary()
    
    async def summarize_batch(
        self, 
        emails: List[Dict[str, Any]]
    ) -> List[EmailSummary]:
        """
        Summarize multiple emails.
        
        Args:
            emails: List of email dictionaries with sender, subject, body, received_at
        
        Returns:
            List of EmailSummary objects
        """
        summaries = []
        
        for email in emails:
            summary = await self.summarize_email(
                sender=email.get("sender", "Unknown"),
                subject=email.get("subject", ""),
                body=email.get("body_text", email.get("body_preview", "")),
                date=email.get("received_at")
            )
            summaries.append(summary)
        
        return summaries
    
    async def generate_digest(
        self, 
        emails: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a daily digest from email summaries.
        
        Args:
            emails: List of email dictionaries with summaries
        
        Returns:
            Dictionary with digest content
        """
        if not emails:
            return {
                "overall_summary": "No emails to summarize.",
                "top_emails": [],
                "all_action_items": [],
                "patterns": "No patterns detected."
            }
        
        # Format email summaries for the prompt
        email_summaries = []
        for i, email in enumerate(emails[:20], 1):  # Limit to 20 emails
            summary_text = f"""
Email {i}:
- From: {email.get('sender', 'Unknown')}
- Subject: {email.get('subject', 'No Subject')}
- Summary: {email.get('summary', 'No summary')}
- Action Items: {', '.join(email.get('action_items', [])) or 'None'}
- Urgency: {email.get('urgency', 'normal')}
- Category: {email.get('category', 'other')}
"""
            email_summaries.append(summary_text)
        
        prompt = self.DIGEST_PROMPT.format(
            email_summaries="\n".join(email_summaries)
        )
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.content[0].text
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Error generating digest: {e}")
            return {
                "overall_summary": f"Received {len(emails)} emails today.",
                "top_emails": [],
                "all_action_items": [],
                "patterns": "Unable to analyze patterns."
            }
    
    async def query_emails(
        self, 
        query: str,
        emails: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Answer natural language queries about emails.
        
        Args:
            query: User's question
            emails: Relevant emails to search through
            conversation_history: Previous messages in conversation
        
        Returns:
            Natural language response
        """
        # Format email context
        email_context = []
        for i, email in enumerate(emails[:10], 1):  # Limit context
            context = f"""
Email {i}:
- From: {email.get('sender', 'Unknown')}
- Subject: {email.get('subject', 'No Subject')}
- Date: {email.get('received_at', 'Unknown')}
- Summary: {email.get('summary', email.get('snippet', 'No summary'))}
- Category: {email.get('category', 'other')}
- Urgency: {email.get('urgency', 'normal')}
"""
            email_context.append(context)
        
        prompt = self.CHAT_QUERY_PROMPT.format(
            query=query,
            email_context="\n".join(email_context) if email_context else "No emails found."
        )
        
        # Build messages with conversation history
        messages = []
        if conversation_history:
            for msg in conversation_history[-5:]:  # Keep last 5 messages
                messages.append(msg)
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=messages
            )

            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error querying emails: {e}")
            return "I'm sorry, I encountered an error while processing your query. Please try again."
    
    def _parse_urgency(self, value: str) -> UrgencyLevel:
        """Parse urgency string to enum."""
        value = value.lower().strip()
        if value == "urgent":
            return UrgencyLevel.URGENT
        elif value == "low":
            return UrgencyLevel.LOW
        return UrgencyLevel.NORMAL
    
    def _parse_category(self, value: str) -> EmailCategory:
        """Parse category string to enum."""
        value = value.lower().strip()
        category_map = {
            "work": EmailCategory.WORK,
            "personal": EmailCategory.PERSONAL,
            "finance": EmailCategory.FINANCE,
            "newsletter": EmailCategory.NEWSLETTER,
            "shopping": EmailCategory.SHOPPING,
        }
        return category_map.get(value, EmailCategory.OTHER)
    
    def _fallback_summary(self) -> EmailSummary:
        """Return a fallback summary when processing fails."""
        return EmailSummary(
            summary="Unable to generate summary. Please review the email manually.",
            key_points=[],
            action_items=[],
            urgency=UrgencyLevel.NORMAL,
            category=EmailCategory.OTHER
        )
