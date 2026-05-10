"""
Services package for EmailGuardian.
Contains business logic for email fetching, summarization, and scheduling.
"""

from app.services.email_fetcher import EmailFetcherService
from app.services.summarizer import SummarizerService
from app.services.classifier import ClassifierService
from app.services.scheduler import SchedulerService

__all__ = [
    "EmailFetcherService",
    "SummarizerService", 
    "ClassifierService",
    "SchedulerService",
]
