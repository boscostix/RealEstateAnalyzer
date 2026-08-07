"""Focused SQLAlchemy repositories for Phase 2 persistence."""

from app.db.repositories.analysis_repository import AnalysisRepository
from app.db.repositories.property_repository import PropertyRepository

__all__ = [
    "AnalysisRepository",
    "PropertyRepository",
]
