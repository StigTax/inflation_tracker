import os
from contextlib import contextmanager
import re
from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, declared_attr


DB_URL = os.getenv('DB_URL', 'sqlite:///./test.db')

_engine = None
_SessionLocal = None


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
        default=datetime.utcnow
    )
    to_update = Column(DateTime, nullable=True)


Base = declarative_base(cls=PreBase)


def init_db(db_url: str, echo: bool = False):
    global DB_URL, _engine, _SessionLocal

    if db_url:
        DB_URL = db_url

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
        expire_on_commit=False
    )


init_db(DB_URL)


@contextmanager
def get_session():
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()
