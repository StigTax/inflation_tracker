from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from app.core.db import Base


class Store(Base):
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    purchases = relationship('Purchase', back_populates='store')

    def __repr__(self) -> str:
        return f'<Store id={self.id} name={self.name!r}>'

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description
        }
