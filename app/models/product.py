from sqlalchemy import (
    Column, Integer, String,
    ForeignKey
)
from sqlalchemy.orm import relationship

from app.core.db import Base


class Product(Base):
    name = Column(
        String(500),
        nullable=False,
        comment='Название продукта',
    )
    category_id = Column(
        Integer,
        ForeignKey('category.id')
    )
    category = relationship(
        'Category',
        back_populates='products'
    )
    measure_type = Column(
        String(25),
        nullable=False,
        comment='Тип единицы измерения',
    )
    unit = Column(
        String(25),
        nullable=False,
        comment='Единица измерения',
    )
    purchases = relationship(
        'Purchase',
        back_populates='product',
    )

    def __repr__(self) -> str:
        return f'<Product id={self.id} name={self.name!r}>'

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "measure_type": self.measure_type,
            "unit": self.unit
        }
