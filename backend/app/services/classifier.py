"""
Email classification service.
Provides additional classification logic and filtering.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.schemas import UrgencyLevel, EmailCategory

logger = logging.getLogger(__name__)


class ClassifierService:
    """Service for classifying and filtering emails."""
    
    # Keywords for urgency detection
    URGENT_KEYWORDS = [
        "urgent", "asap", "immediately", "deadline", "today",
        "critical", "emergency", "time-sensitive", "action required",
        "respond immediately", "expires today", "final notice"
    ]
    
    LOW_PRIORITY_KEYWORDS = [
        "newsletter", "unsubscribe", "weekly digest", "monthly update",
        "no action needed", "fyi", "just letting you know"
    ]
    
    # Patterns for category detection
    CATEGORY_PATTERNS = {
        EmailCategory.FINANCE: [
            r"bank", r"statement", r"payment", r"invoice", r"receipt",
            r"transaction", r"credit card", r"balance", r"\$\d+",
            r"paypal", r"venmo", r"zelle"
        ],
        EmailCategory.SHOPPING: [
            r"order", r"shipped", r"delivered", r"tracking",
            r"amazon", r"ebay", r"etsy", r"your order",
            r"shipment", r"delivery"
        ],
        EmailCategory.NEWSLETTER: [
            r"newsletter", r"subscribe", r"unsubscribe", r"weekly",
            r"digest", r"updates? from", r"new from", r"roundup"
        ],
        EmailCategory.WORK: [
            r"meeting", r"project", r"deadline", r"review",
            r"sprint", r"standup", r"agenda", r"presentation",
            r"report", r"quarterly"
        ],
        EmailCategory.PERSONAL: [
            r"birthday", r"congratulations", r"thank you",
            r"invitation", r"party", r"family"
        ],
    }
    
    # Spam-like patterns to filter
    SPAM_PATTERNS = [
        r"you('ve)? won", r"lottery", r"prize winner",
        r"nigerian prince", r"million dollars",
        r"act now", r"limited time", r"click here",
        r"100% free", r"risk.?free", r"no obligation"
    ]
    
    def __init__(self):
        """Initialize the classifier."""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for performance."""
        self.urgent_pattern = re.compile(
            "|".join(self.URGENT_KEYWORDS), 
            re.IGNORECASE
        )
        self.low_priority_pattern = re.compile(
            "|".join(self.LOW_PRIORITY_KEYWORDS),
            re.IGNORECASE
        )
        self.spam_pattern = re.compile(
            "|".join(self.SPAM_PATTERNS),
            re.IGNORECASE
        )
        
        self.category_patterns = {}
        for category, patterns in self.CATEGORY_PATTERNS.items():
            self.category_patterns[category] = re.compile(
                "|".join(patterns),
                re.IGNORECASE
            )
    
    def detect_urgency(
        self, 
        subject: str, 
        body: str,
        labels: Optional[List[str]] = None
    ) -> UrgencyLevel:
        """
        Detect email urgency based on content and labels.
        
        Args:
            subject: Email subject
            body: Email body text
            labels: Gmail labels
        
        Returns:
            UrgencyLevel enum value
        """
        text = f"{subject} {body}"
        
        # Check Gmail importance labels
        if labels:
            if "IMPORTANT" in labels:
                return UrgencyLevel.URGENT
            if "CATEGORY_PROMOTIONS" in labels:
                return UrgencyLevel.LOW
            if "CATEGORY_UPDATES" in labels:
                return UrgencyLevel.LOW
        
        # Check for urgent keywords
        if self.urgent_pattern.search(text):
            return UrgencyLevel.URGENT
        
        # Check for low priority indicators
        if self.low_priority_pattern.search(text):
            return UrgencyLevel.LOW
        
        return UrgencyLevel.NORMAL
    
    def detect_category(
        self, 
        subject: str, 
        body: str,
        sender_email: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> EmailCategory:
        """
        Detect email category based on content.
        
        Args:
            subject: Email subject
            body: Email body text
            sender_email: Sender's email address
            labels: Gmail labels
        
        Returns:
            EmailCategory enum value
        """
        text = f"{subject} {body}"
        
        # Check Gmail category labels first
        if labels:
            label_map = {
                "CATEGORY_SOCIAL": EmailCategory.PERSONAL,
                "CATEGORY_UPDATES": EmailCategory.NEWSLETTER,
                "CATEGORY_PROMOTIONS": EmailCategory.SHOPPING,
                "CATEGORY_FORUMS": EmailCategory.NEWSLETTER,
            }
            for label, category in label_map.items():
                if label in labels:
                    return category
        
        # Check sender domain for common patterns
        if sender_email:
            sender_lower = sender_email.lower()
            domain_patterns = {
                EmailCategory.SHOPPING: ["amazon", "ebay", "etsy", "shopify"],
                EmailCategory.FINANCE: ["paypal", "bank", "chase", "wells", "citi"],
                EmailCategory.NEWSLETTER: ["substack", "mailchimp", "newsletter"],
            }
            for category, domains in domain_patterns.items():
                if any(domain in sender_lower for domain in domains):
                    return category
        
        # Check content patterns
        category_scores = {}
        for category, pattern in self.category_patterns.items():
            matches = len(pattern.findall(text))
            if matches > 0:
                category_scores[category] = matches
        
        if category_scores:
            # Return category with highest match count
            return max(category_scores, key=category_scores.get)
        
        return EmailCategory.OTHER
    
    def is_likely_spam(
        self, 
        subject: str, 
        body: str,
        sender_email: Optional[str] = None
    ) -> Tuple[bool, float]:
        """
        Check if email is likely spam.
        
        Args:
            subject: Email subject
            body: Email body text
            sender_email: Sender's email address
        
        Returns:
            Tuple of (is_spam, confidence_score)
        """
        text = f"{subject} {body}"
        
        # Check spam patterns
        spam_matches = len(self.spam_pattern.findall(text))
        
        # Calculate spam score (0-1)
        spam_score = min(spam_matches * 0.2, 1.0)
        
        # Additional spam indicators
        if sender_email:
            # Check for suspicious sender patterns
            if re.search(r"\d{5,}", sender_email):  # Many numbers in email
                spam_score += 0.2
            if len(sender_email) > 50:  # Very long email address
                spam_score += 0.1
        
        # Check subject line
        if subject:
            if subject.isupper():  # ALL CAPS subject
                spam_score += 0.15
            if "!!!" in subject or "???" in subject:  # Excessive punctuation
                spam_score += 0.1
            if re.search(r"RE:\s*RE:\s*RE:", subject, re.IGNORECASE):  # Chain replies
                spam_score += 0.05
        
        is_spam = spam_score >= 0.5
        return is_spam, min(spam_score, 1.0)
    
    def filter_emails(
        self, 
        emails: List[Dict[str, Any]],
        exclude_spam: bool = True,
        min_urgency: Optional[UrgencyLevel] = None,
        categories: Optional[List[EmailCategory]] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter a list of emails based on criteria.
        
        Args:
            emails: List of email dictionaries
            exclude_spam: Whether to filter out likely spam
            min_urgency: Minimum urgency level to include
            categories: Categories to include (None = all)
        
        Returns:
            Filtered list of emails
        """
        filtered = []
        
        urgency_order = {
            UrgencyLevel.LOW: 0,
            UrgencyLevel.NORMAL: 1,
            UrgencyLevel.URGENT: 2,
        }
        
        for email in emails:
            # Check spam
            if exclude_spam:
                is_spam, _ = self.is_likely_spam(
                    email.get("subject", ""),
                    email.get("body_text", ""),
                    email.get("sender_email")
                )
                if is_spam:
                    continue
            
            # Check urgency
            if min_urgency:
                email_urgency = email.get("urgency", UrgencyLevel.NORMAL)
                if urgency_order.get(email_urgency, 1) < urgency_order.get(min_urgency, 0):
                    continue
            
            # Check category
            if categories:
                email_category = email.get("category", EmailCategory.OTHER)
                if email_category not in categories:
                    continue
            
            filtered.append(email)
        
        return filtered
    
    def enrich_email(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add classification data to an email.
        
        Args:
            email: Email dictionary
        
        Returns:
            Email with added urgency and category
        """
        subject = email.get("subject", "")
        body = email.get("body_text", email.get("body_preview", ""))
        sender_email = email.get("sender_email")
        labels = email.get("labels", [])
        
        # Only set if not already present
        if "urgency" not in email:
            email["urgency"] = self.detect_urgency(subject, body, labels)
        
        if "category" not in email:
            email["category"] = self.detect_category(
                subject, body, sender_email, labels
            )
        
        # Add spam score
        is_spam, spam_score = self.is_likely_spam(subject, body, sender_email)
        email["spam_score"] = spam_score
        email["is_likely_spam"] = is_spam
        
        return email
    
    def get_email_priority_score(self, email: Dict[str, Any]) -> float:
        """
        Calculate a priority score for email sorting.
        Higher score = higher priority.
        
        Args:
            email: Email dictionary with urgency and category
        
        Returns:
            Float priority score (0-1)
        """
        score = 0.5  # Base score
        
        # Urgency contribution (0-0.4)
        urgency = email.get("urgency", UrgencyLevel.NORMAL)
        urgency_scores = {
            UrgencyLevel.URGENT: 0.4,
            UrgencyLevel.NORMAL: 0.2,
            UrgencyLevel.LOW: 0.0,
        }
        score += urgency_scores.get(urgency, 0.2)
        
        # Category contribution (0-0.2)
        category = email.get("category", EmailCategory.OTHER)
        category_scores = {
            EmailCategory.WORK: 0.2,
            EmailCategory.FINANCE: 0.15,
            EmailCategory.PERSONAL: 0.1,
            EmailCategory.SHOPPING: 0.05,
            EmailCategory.NEWSLETTER: 0.0,
            EmailCategory.OTHER: 0.05,
        }
        score += category_scores.get(category, 0.05)
        
        # Recency bonus (0-0.1)
        received_at = email.get("received_at")
        if received_at:
            if isinstance(received_at, str):
                received_at = datetime.fromisoformat(received_at)
            hours_old = (datetime.utcnow() - received_at).total_seconds() / 3600
            if hours_old < 1:
                score += 0.1
            elif hours_old < 6:
                score += 0.05
        
        # Unread bonus
        if not email.get("is_read", False):
            score += 0.05
        
        return min(score, 1.0)
