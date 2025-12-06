import os
from contextlib import contextmanager
import re

from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, declared_attr


DB_URL = os.getenv('DB_URL', 'sqlite:///./test.db')


class PreBase:
    @declared_attr
    def __tablename__(cls):
        name = cls.__name__
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s1).lower()

    id = Column(Integer, primary_key=True)


Base = declarative_base(cls=PreBase)

engine = create_engine(
    DB_URL,
    connect_args=(
        {"check_same_thread": False}
        if DB_URL.startswith("sqlite") else {}
    ),
    future=True,
)

SessionLocal = sessionmaker(
    engine,
    autoflush=False,
    expire_on_commit=False
)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
