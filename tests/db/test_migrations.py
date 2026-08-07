"""Migration smoke tests for persisted-property and analysis storage."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command


def test_alembic_upgrade_creates_persistence_tables_and_indexes(tmp_path: Path) -> None:
    database_path = tmp_path / "milestone6_migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{database_path}")

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite+pysqlite:///{database_path}")
    inspector = inspect(engine)
    assert "properties" in inspector.get_table_names()
    assert "analyses" in inspector.get_table_names()
    property_indexes = {index["name"] for index in inspector.get_indexes("properties")}
    analysis_indexes = {index["name"] for index in inspector.get_indexes("analyses")}
    unique_constraints = inspector.get_unique_constraints("analyses")

    assert "ix_properties_provider" in property_indexes
    assert "ix_properties_full_address" in property_indexes
    assert "ix_analyses_property_created" in analysis_indexes
    assert any(
        constraint["name"] == "uq_analyses_property_version" for constraint in unique_constraints
    )
    engine.dispose()
