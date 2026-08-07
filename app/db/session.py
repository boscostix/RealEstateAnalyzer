"""Database engine and session helpers."""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///./real_estate.db"


def get_database_url() -> str:
    """Return the configured database URL for the application."""

    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def create_engine_from_url(database_url: str | None = None) -> Engine:
    """Create an engine suitable for the configured backend."""

    url = database_url or get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, connect_args=connect_args)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build the shared session factory used by repositories and tests."""

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


engine = create_engine_from_url()
SessionLocal = create_session_factory(engine)


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
