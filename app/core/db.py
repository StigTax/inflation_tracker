"""Подключение и управление базой данных."""

from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, declared_attr, sessionmaker

from app.core.settings import get_db_url

DB_URL: Optional[str] = None
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


class PreBase:
    @declared_attr
    def __tablename__(cls):
        name = cls.__name__
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s1).lower()

    id = Column(Integer, primary_key=True)
    to_create = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    to_update = Column(DateTime, nullable=True)


Base = declarative_base(cls=PreBase)


def init_db(db_url: Optional[str] = None, echo: bool = False) -> None:
    """Инициализировать engine и sessionmaker.

    Args:
        db_url: URL базы данных. Если None — вычисляется через
        settings.get_db_url().
        echo: Включить SQL echo.

    Returns:
        None
    """
    global DB_URL, _engine, _SessionLocal

    DB_URL = get_db_url(override=db_url)

    _engine = create_engine(
        DB_URL,
        echo=echo,
        connect_args=(
            {'check_same_thread': False} if DB_URL.startswith('sqlite') else {}
        ),
        future=True,
    )

    _SessionLocal = sessionmaker(
        bind=_engine,
        autoflush=False,
        expire_on_commit=False,
    )


def _ensure_inited() -> None:
    """Гарантировать, что база инициализирована.

    Returns:
        None
    """
    if _SessionLocal is None:
        init_db()


@contextmanager
def get_session():
    """Получить сессию SQLAlchemy.

    Returns:
        Session: SQLAlchemy session (context manager).
    """
    _ensure_inited()
    session = _SessionLocal()  # type: ignore[misc]
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope():
    """Скоуп для транзакций с rollback на ошибках.

    Returns:
        Session: SQLAlchemy session (context manager).
    """
    with get_session() as session:
        try:
            yield session
        except IntegrityError as e:
            session.rollback()
            raise RuntimeError(
                'Конфликт уникальности / целостности данных',
            ) from e
        except Exception:
            session.rollback()
            raise
