"""Migration smoke tests for Milestone 6 Phase 1."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command


def test_alembic_upgrade_creates_phase1_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "phase1_migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{database_path}")

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite+pysqlite:///{database_path}")
    inspector = inspect(engine)
    assert "properties" in inspector.get_table_names()
    assert "analyses" in inspector.get_table_names()
    unique_constraints = inspector.get_unique_constraints("analyses")
    assert any(
        constraint["name"] == "uq_analyses_property_version" for constraint in unique_constraints
    )
    engine.dispose()
