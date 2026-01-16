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
        nullable=False
    )
    product = relationship(
        'Product',
        back_populates='purchases'
    )
    store_id = Column(Integer, ForeignKey('store.id'))
    store = relationship(
        'Store',
        back_populates='purchases'
    )
    purchase_date = Column(
        Date,
        nullable=False,
        default=date.today
    )

    quantity = Column(
        Float,
        nullable=False
    )
    total_price = Column(
        Float,
        nullable=False
    )
    unit_price = Column(
        Float,
        nullable=False
    )
    comment = Column(Text)
