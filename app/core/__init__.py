"""Shared init for core package."""

from app.core.config import settings  # noqa: F401

# Lazy imports — don't import database at package level to avoid
# requiring asyncpg for tests that don't use the database.
def _import_database():
    from app.core.database import async_session, engine, get_db  # noqa: F401
    return async_session, engine, get_db
