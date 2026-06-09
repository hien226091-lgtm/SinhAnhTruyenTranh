"""Database connection utilities using SQLAlchemy.

This module exposes an engine, a session factory, a declarative `Base`, and
helpers to initialize the database and provide sessions to FastAPI endpoints.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session


# Declarative base for ORM models
Base = declarative_base()


def get_database_url() -> str:
    """Read `DATABASE_URL` from environment (empty string if unset)."""
    return os.getenv("DATABASE_URL", "")


def create_db_engine(url: str):
    """Create a SQLAlchemy engine. Caller should ensure `url` is non-empty."""
    # echo=False to avoid noisy SQL logs by default
    return create_engine(url, pool_pre_ping=True)


# Module-level engine and session factory; created lazily in `init_db`
engine = None
SessionLocal: sessionmaker | None = None


def init_db(url: str | None = None) -> None:
    """Initialize the DB engine and session factory.

    If `url` is None the `DATABASE_URL` env var will be used. This function
    also ensures that ORM `Base.metadata.create_all` can be called by the
    caller (e.g. a create-tables script).
    """
    global engine, SessionLocal
    db_url = url or get_database_url()
    if not db_url:
        # Leave engine as None if no URL configured; caller can handle this.
        return
    engine = create_db_engine(db_url)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def get_db_session() -> Iterator[Session]:
    """Yield a SQLAlchemy Session and ensure it is closed after use.

    Usage in FastAPI endpoints (sync) can be via `with get_db_session() as db:`
    or by importing the contextmanager for dependency injection.
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first and ensure DATABASE_URL is set.")
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db() -> Iterator[Session]:
    """FastAPI-compatible dependency generator that yields a DB session."""
    with get_db_session() as db:
        yield db


def create_tables() -> None:
    """Create all tables defined on the ORM `Base`.

    Requires `init_db()` to have been called and `engine` to be configured.
    """
    if engine is None:
        raise RuntimeError("Database engine not initialized. Call init_db() first.")
    # Create any missing tables
    Base.metadata.create_all(bind=engine)

    # Ensure `FullName` column exists on `users` table for backwards compatibility
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if "users" in tables:
            cols = [c["name"] for c in inspector.get_columns("users")]
            if "FullName" not in cols:
                # Best-effort ALTER TABLE for common SQL engines (MySQL/Postgres/SQLite).
                # Use VARCHAR(255) and allow NULL so it won't block existing rows.
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN FullName VARCHAR(255) NULL"))
    except Exception:
        # Don't fail table creation on migration attempts; log optional in future.
        pass

