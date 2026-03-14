"""Alembic environment configuration for backend database migrations."""

from __future__ import annotations

import importlib
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

importlib.import_module("app.models")
settings = importlib.import_module("app.core.config").settings

config = context.config
configure_logger = config.attributes.get("configure_logger", True)

if config.config_file_name is not None and configure_logger:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def _normalize_database_url(database_url: str) -> str:
    if "://" not in database_url:
        return database_url
    scheme, rest = database_url.split("://", 1)
    if scheme in ("postgresql", "postgres"):
        return f"postgresql+psycopg://{rest}"
    return database_url


def get_url() -> str:
    """Return the normalized SQLAlchemy database URL for Alembic."""
    return _normalize_database_url(settings.database_url)


config.set_main_option("sqlalchemy.url", get_url())


def _version_table_kwargs() -> dict:
    """Return version_table_schema kwarg if DB_SCHEMA is set."""
    schema = getattr(settings, "db_schema", "").strip()
    if schema:
        return {"version_table_schema": schema}
    return {}


def run_migrations_offline() -> None:
    """Run migrations in offline mode without DB engine connectivity."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        **_version_table_kwargs(),
    )

    with context.begin_transaction():
        context.run_migrations()


def _connect_args() -> dict:
    """Build connect_args, including search_path if DB_SCHEMA is set."""
    schema = getattr(settings, "db_schema", "").strip()
    if schema:
        return {"options": f"-csearch_path={schema},public"}
    return {}


def run_migrations_online() -> None:
    """Run migrations in online mode using a live DB connection."""
    from sqlalchemy import create_engine, text

    engine = create_engine(
        get_url(),
        poolclass=pool.NullPool,
        connect_args=_connect_args(),
    )

    with engine.connect() as connection:
        # Ensure the target schema exists before running migrations.
        schema = getattr(settings, "db_schema", "").strip()
        if schema:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            **_version_table_kwargs(),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
