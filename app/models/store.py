from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from app.core.db import Base


class Store(Base):
    name = Column(
        String(255),
        nullable=False,
        unique=True,
    )
    description = Column(Text)

    #  ----- Связи -----
    purchases = relationship(
        'Purchase',
        back_populates='store',
    )

    def __repr__(self) -> str:
        return self.name

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
        }
