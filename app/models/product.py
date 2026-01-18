from __future__ import annotations

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
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
        ForeignKey('category.id'),
        nullable=True,
    )
    unit_id = Column(
        Integer,
        ForeignKey('unit.id'),
        nullable=False,
    )

    #  ----- Связи -----
    category = relationship(
        'Category',
        back_populates='products',
    )
    purchases = relationship(
        'Purchase',
        back_populates='product',
    )
    unit = relationship(
        'Unit',
        back_populates='product',
    )

    def __repr__(self) -> str:
        return f'{self.name}'

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'category_id': self.category_id,
            'category': getattr(self.category, 'name', None),
            'unit_id': self.unit_id,
            'measure_type': getattr(self.unit, 'measure_type', None),
            'unit': getattr(self.unit, 'unit', None),
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

    #  ----- Связи -----
    product = relationship(
        'Product',
        back_populates='unit',
    )

    def __repr__(self) -> str:
        return f'{self.measure_type} ({self.unit})'

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "unit": self.unit,
            "measure_type": self.measure_type,
        }
