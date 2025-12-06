from sqlalchemy import (
    Column, Integer, String,
    ForeignKey
)
from sqlalchemy.orm import relationship

from app.core.db import Base


class Product(Base):
    name = Column(String(500), nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship('Category', back_populates='products')
    measure_type = Column(String(25), nullable=False)
    unit = Column(String(25), nullable=False)
    purchases = relationship('Purchase', back_populates='product')
