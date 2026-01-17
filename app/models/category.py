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
    description = Column(Text, comment='Описание категории')
    products = relationship('Product', back_populates='category')
