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

    # ----- Связи ----- #
    product = relationship(
        'Product',
        back_populates='purchases'
    )
    store = relationship(
        'Store',
        back_populates='purchases'
    )
