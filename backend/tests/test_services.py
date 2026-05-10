"""
Tests for EmailGuardian services.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from app.services.classifier import ClassifierService
from app.schemas import UrgencyLevel, EmailCategory


class TestClassifierService:
    """Tests for the ClassifierService."""
    
    @pytest.fixture
    def classifier(self):
        return ClassifierService()
    
    def test_detect_urgency_urgent_keywords(self, classifier):
        """Test urgency detection with urgent keywords."""
        # Test urgent keywords
        assert classifier.detect_urgency(
            "URGENT: Meeting today",
            "Please respond immediately"
        ) == UrgencyLevel.URGENT
        
        assert classifier.detect_urgency(
            "Action required: Deadline approaching",
            "This needs your attention ASAP"
        ) == UrgencyLevel.URGENT
    
    def test_detect_urgency_low_priority(self, classifier):
        """Test urgency detection for low priority emails."""
        assert classifier.detect_urgency(
            "Weekly Newsletter",
            "Here's your weekly update. No action needed."
        ) == UrgencyLevel.LOW
        
        assert classifier.detect_urgency(
            "FYI: Company Updates",
            "Just letting you know about recent changes."
        ) == UrgencyLevel.LOW
    
    def test_detect_urgency_normal(self, classifier):
        """Test urgency detection for normal priority emails."""
        assert classifier.detect_urgency(
            "Meeting notes from yesterday",
            "Here are the notes from our discussion."
        ) == UrgencyLevel.NORMAL
    
    def test_detect_urgency_with_labels(self, classifier):
        """Test urgency detection with Gmail labels."""
        # IMPORTANT label should be urgent
        assert classifier.detect_urgency(
            "Regular subject",
            "Regular body",
            labels=["IMPORTANT"]
        ) == UrgencyLevel.URGENT
        
        # CATEGORY_PROMOTIONS should be low
        assert classifier.detect_urgency(
            "Sale!",
            "Big discounts",
            labels=["CATEGORY_PROMOTIONS"]
        ) == UrgencyLevel.LOW
    
    def test_detect_category_finance(self, classifier):
        """Test category detection for finance emails."""
        assert classifier.detect_category(
            "Your bank statement is ready",
            "Your monthly statement for account ending in 1234"
        ) == EmailCategory.FINANCE
        
        assert classifier.detect_category(
            "Payment received",
            "We received your payment of $100"
        ) == EmailCategory.FINANCE
    
    def test_detect_category_shopping(self, classifier):
        """Test category detection for shopping emails."""
        assert classifier.detect_category(
            "Your order has shipped",
            "Tracking number: 1234567890"
        ) == EmailCategory.SHOPPING
        
        assert classifier.detect_category(
            "Delivery update",
            "Your package will be delivered tomorrow"
        ) == EmailCategory.SHOPPING
    
    def test_detect_category_work(self, classifier):
        """Test category detection for work emails."""
        assert classifier.detect_category(
            "Project deadline reminder",
            "Please submit your report by Friday"
        ) == EmailCategory.WORK
        
        assert classifier.detect_category(
            "Meeting agenda for standup",
            "Here's the agenda for today's meeting"
        ) == EmailCategory.WORK
    
    def test_detect_category_newsletter(self, classifier):
        """Test category detection for newsletters."""
        assert classifier.detect_category(
            "Weekly newsletter",
            "Click to unsubscribe from this newsletter"
        ) == EmailCategory.NEWSLETTER
    
    def test_detect_category_with_sender_domain(self, classifier):
        """Test category detection using sender email domain."""
        assert classifier.detect_category(
            "Your receipt",
            "Thank you for your purchase",
            sender_email="orders@amazon.com"
        ) == EmailCategory.SHOPPING
        
        assert classifier.detect_category(
            "Account update",
            "Your account has been updated",
            sender_email="alerts@paypal.com"
        ) == EmailCategory.FINANCE
    
    def test_detect_category_with_labels(self, classifier):
        """Test category detection with Gmail labels."""
        assert classifier.detect_category(
            "Subject",
            "Body",
            labels=["CATEGORY_SOCIAL"]
        ) == EmailCategory.PERSONAL
        
        assert classifier.detect_category(
            "Subject",
            "Body",
            labels=["CATEGORY_PROMOTIONS"]
        ) == EmailCategory.SHOPPING
    
    def test_is_likely_spam(self, classifier):
        """Test spam detection."""
        # Should be spam
        is_spam, score = classifier.is_likely_spam(
            "YOU'VE WON THE LOTTERY!!!",
            "Claim your million dollars now! Act now!"
        )
        assert is_spam is True
        assert score >= 0.5
        
        # Should not be spam
        is_spam, score = classifier.is_likely_spam(
            "Meeting tomorrow",
            "Let's discuss the project timeline."
        )
        assert is_spam is False
        assert score < 0.5
    
    def test_enrich_email(self, classifier):
        """Test email enrichment with classification."""
        email = {
            "subject": "URGENT: Project deadline",
            "body_text": "The project deadline is today. Please submit ASAP.",
            "sender_email": "manager@company.com",
            "labels": []
        }
        
        enriched = classifier.enrich_email(email)
        
        assert "urgency" in enriched
        assert "category" in enriched
        assert "spam_score" in enriched
        assert "is_likely_spam" in enriched
        assert enriched["urgency"] == UrgencyLevel.URGENT
        assert enriched["category"] == EmailCategory.WORK
    
    def test_filter_emails(self, classifier):
        """Test email filtering."""
        emails = [
            {
                "subject": "Urgent work email",
                "body_text": "Important meeting today",
                "urgency": UrgencyLevel.URGENT,
                "category": EmailCategory.WORK,
            },
            {
                "subject": "Newsletter",
                "body_text": "Weekly updates",
                "urgency": UrgencyLevel.LOW,
                "category": EmailCategory.NEWSLETTER,
            },
            {
                "subject": "Bank statement",
                "body_text": "Your monthly statement",
                "urgency": UrgencyLevel.NORMAL,
                "category": EmailCategory.FINANCE,
            },
        ]
        
        # Filter by urgency
        urgent_only = classifier.filter_emails(
            emails,
            min_urgency=UrgencyLevel.URGENT
        )
        assert len(urgent_only) == 1
        assert urgent_only[0]["subject"] == "Urgent work email"
        
        # Filter by category
        work_only = classifier.filter_emails(
            emails,
            categories=[EmailCategory.WORK]
        )
        assert len(work_only) == 1
        assert work_only[0]["category"] == EmailCategory.WORK
    
    def test_get_email_priority_score(self, classifier):
        """Test priority score calculation."""
        urgent_email = {
            "urgency": UrgencyLevel.URGENT,
            "category": EmailCategory.WORK,
            "is_read": False,
            "received_at": datetime.utcnow()
        }
        
        low_email = {
            "urgency": UrgencyLevel.LOW,
            "category": EmailCategory.NEWSLETTER,
            "is_read": True,
            "received_at": datetime.utcnow()
        }
        
        urgent_score = classifier.get_email_priority_score(urgent_email)
        low_score = classifier.get_email_priority_score(low_email)
        
        assert urgent_score > low_score
        assert 0 <= urgent_score <= 1
        assert 0 <= low_score <= 1


class TestEmailParsing:
    """Tests for email parsing functionality."""
    
    def test_parse_sender_email(self):
        """Test parsing sender email from various formats."""
        from email.utils import parseaddr
        
        # Standard format
        name, email = parseaddr("John Doe <john@example.com>")
        assert name == "John Doe"
        assert email == "john@example.com"
        
        # Email only
        name, email = parseaddr("john@example.com")
        assert email == "john@example.com"
        
        # Quoted name
        name, email = parseaddr('"John Doe" <john@example.com>')
        assert name == "John Doe"
        assert email == "john@example.com"
    
    def test_parse_date_string(self):
        """Test parsing email date strings."""
        from email.utils import parsedate_to_datetime
        
        # RFC 2822 format
        date_str = "Mon, 10 Feb 2026 14:30:00 -0500"
        dt = parsedate_to_datetime(date_str)
        assert dt.year == 2026
        assert dt.month == 2
        assert dt.day == 10


@pytest.mark.asyncio
class TestSummarizerService:
    """Tests for the SummarizerService."""
    
    @patch('app.services.summarizer.anthropic.Anthropic')
    async def test_summarize_email_success(self, mock_anthropic):
        """Test successful email summarization."""
        from app.services.summarizer import SummarizerService
        
        # Mock Claude response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text='{"summary": "Test summary", "key_points": ["Point 1"], "action_items": [], "urgency": "normal", "category": "work"}')]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        service = SummarizerService()
        service.client = mock_client
        
        result = await service.summarize_email(
            sender="test@example.com",
            subject="Test Subject",
            body="Test body content"
        )
        
        assert result.summary == "Test summary"
        assert len(result.key_points) == 1
        assert result.urgency == UrgencyLevel.NORMAL
        assert result.category == EmailCategory.WORK
    
    @patch('app.services.summarizer.anthropic.Anthropic')
    async def test_summarize_email_fallback_on_error(self, mock_anthropic):
        """Test fallback when summarization fails."""
        from app.services.summarizer import SummarizerService
        
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic.return_value = mock_client
        
        service = SummarizerService()
        service.client = mock_client
        
        result = await service.summarize_email(
            sender="test@example.com",
            subject="Test Subject",
            body="Test body"
        )
        
        # Should return fallback summary
        assert "Unable to generate summary" in result.summary
        assert result.urgency == UrgencyLevel.NORMAL


class TestSchemaValidation:
    """Tests for Pydantic schema validation."""
    
    def test_email_summary_schema(self):
        """Test EmailSummary schema validation."""
        from app.schemas import EmailSummary
        
        summary = EmailSummary(
            summary="Test summary",
            key_points=["Point 1", "Point 2"],
            action_items=["Action 1"],
            urgency=UrgencyLevel.URGENT,
            category=EmailCategory.WORK
        )
        
        assert summary.summary == "Test summary"
        assert len(summary.key_points) == 2
        assert summary.urgency == UrgencyLevel.URGENT
    
    def test_chat_request_validation(self):
        """Test ChatRequest schema validation."""
        from app.schemas import ChatRequest
        
        # Valid request
        request = ChatRequest(query="Show me urgent emails")
        assert request.query == "Show me urgent emails"
        
        # Empty query should fail
        with pytest.raises(ValueError):
            ChatRequest(query="")
    
    def test_user_settings_validation(self):
        """Test UserSettings schema validation."""
        from app.schemas import UserSettings
        
        # Valid settings
        settings = UserSettings(
            notification_enabled=True,
            digest_enabled=False,
            digest_time="08:00"
        )
        assert settings.digest_time == "08:00"
        
        # Invalid time format
        with pytest.raises(ValueError):
            UserSettings(digest_time="invalid")
