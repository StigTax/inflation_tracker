from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship, validates

from app.core.db import Base


class Purchase(Base):
    product_id = Column(
        Integer,
        ForeignKey('product.id', ondelete='RESTRICT'),
        nullable=False,
        comment='ID продукта',
    )
    store_id = Column(
        Integer,
        ForeignKey('store.id', ondelete='RESTRICT'),
        nullable=False,
        comment='ID магазина',
    )
    purchase_date = Column(
        Date,
        nullable=False,
        default=date.today,
        comment='Дата покупки',
    )
    quantity = Column(
        Numeric(12, 3),
        nullable=False,
        comment='Количество купленного товара',
    )
    total_price = Column(
        Numeric(12, 2),
        nullable=False,
        comment='Общая стоимость покупки',
    )
    regular_unit_price = Column(
        Numeric(12, 2),
        nullable=True,
        comment='Обычная цена за единицу (без акции), если известна',
    )
    is_promo = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default='0',
        comment='Товар по акции или нет.'
    )
    promo_type = Column(
        String(32),
        nullable=True,
        comment=(
            'Тип акции: discount/multi_buy/loyalty/clearance/coupon/cashback'
        ),
    )
    comment = Column(Text, comment='Комментарий к покупке')

    #  ----- Связи -----
    product = relationship(
        'Product',
        back_populates='purchases',
    )
    store = relationship(
        'Store',
        back_populates='purchases',
    )

    @property
    def unit_price(self) -> Decimal:
        '''Цена за единицу — вычисляемая, чтобы не было рассинхрона.'''
        if not self.quantity:
            return Decimal('0')
        return (
            Decimal(self.total_price) / Decimal(self.quantity)
        ).quantize(Decimal('0.01'))

    @property
    def effective_regular_unit_price(self) -> Decimal:
        if self.regular_unit_price is not None:
            return (
                Decimal(str(self.regular_unit_price)).quantize(
                    Decimal('0.01')
                )
            )
        return self.unit_price

    @validates('quantity', 'total_price')
    def _validate_non_negative(self, key, value):
        if value is None:
            return value
        if Decimal(value) < 0:
            raise ValueError(f'{key} не может быть отрицательным')
        return value

    @validates('is_promo')
    def _validate_is_promo(self, key, value):
        if not value:
            self.promo_type = None
            self.regular_unit_price = None
        return value

    def to_dict(self) -> dict:
        product = self.product
        unit = getattr(product, 'unit', None)
        category = getattr(product, 'category', None)

        return {
            'id': self.id,
            'purchase_date': self.purchase_date,

            'product_id': self.product_id,
            'product': getattr(product, 'name', None),

            'category': getattr(category, 'name', None),
            'category_id': getattr(product, 'category_id', None),
            'measure_type': getattr(unit, 'measure_type', None),
            'unit': getattr(unit, 'unit', None),

            'store_id': self.store_id,
            'store': getattr(self.store, 'name', None),

            'quantity': float(
                self.quantity
            ) if self.quantity is not None else None,
            'total_price': float(
                self.total_price
            ) if self.total_price is not None else None,
            'unit_price': float(
                self.unit_price
            ) if self.unit_price is not None else None,

            'is_promo': self.is_promo,
            'promo_type': self.promo_type,
            'regular_unit_price': float(
                self.regular_unit_price
            ) if self.regular_unit_price is not None else None,

            'comment': self.comment,
        }
