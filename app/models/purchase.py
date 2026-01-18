from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Column, Integer, Date,
    ForeignKey, Float, Text
)
from sqlalchemy.orm import relationship

from app.core.db import Base


class Purchase(Base):
    product_id = Column(
        Integer,
        ForeignKey('product.id'),
        nullable=False,
        comment='ID продукта',
    )
    store_id = Column(
        Integer,
        ForeignKey('store.id'),
        nullable=True,
        comment='ID магазина',
    )
    purchase_date = Column(
        Date,
        nullable=False,
        default=date.today,
        comment='Дата покупки',
    )
    quantity = Column(
        Float,
        nullable=False,
        comment='Количество купленного товара',
    )
    total_price = Column(
        Float,
        nullable=False,
        comment='Общая стоимость покупки',
    )
    unit_price = Column(
        Float,
        nullable=False,
        comment='Цена за единицу товара'
    )
    comment = Column(Text, comment='Комментарий к покупке')

    #  ----- Связи -----
    product = relationship(
        'Product',
        back_populates='purchases'
    )
    store = relationship(
        'Store',
        back_populates='purchases'
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'purchase_date': self.purchase_date,
            'product_id': self.product_id,
            'product': getattr(self.product, 'name', None),
            'store_id': self.store_id,
            'store': getattr(self.store, 'name', None),
            'quantity': self.quantity,
            'total_price': self.total_price,
            'unit_price': self.unit_price,
            'comment': self.comment,
        }
