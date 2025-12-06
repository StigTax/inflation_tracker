from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from app.core.db import Base


class Category(Base):
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    products = relationship('Product', back_populates='category')
