"""Declarative base for SQLAlchemy ORM models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""


import app.db.models  # noqa: E402,F401
