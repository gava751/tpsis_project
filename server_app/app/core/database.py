"""Фабрика SQLAlchemy Engine/Session и общий реестр ORM-моделей."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей серверного приложения."""


def create_engine_from_url(db_url: str | None = None):
    return create_engine(db_url or settings.db_url, pool_pre_ping=True, future=True)


def make_session_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
