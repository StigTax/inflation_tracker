from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from app.core.db import Base


class Category(Base):
    name = Column(
        String(255),
        nullable=False,
        unique=True,
        comment='Название категории',
    )
    description = Column(
        Text,
        comment='Описание категории'
    )

    #  ----- Связи -----
    products = relationship(
        'Product',
        back_populates='category'
    )

    def __repr__(self) -> str:
        return self.name

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description
        }
