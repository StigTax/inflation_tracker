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
    unit_id = Column(
        Integer,
        ForeignKey('unit.id')
    )

    #  ----- Связи -----
    category = relationship(
        'Category',
        back_populates='products'
    )
    purchases = relationship(
        'Purchase',
        back_populates='product',
    )
    units = relationship(
        'Unit',
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


class Unit(Base):
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

    def __repr__(self) -> str:
        return f'<Unit id={self.id} name={self.name!r}>'

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "unit": self.unit,
            "measure_type": self.measure_type
        }
