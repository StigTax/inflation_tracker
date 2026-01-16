from typing import Optional
from datetime import datetime

from app.core.db import get_session
from app.models import Category


def create_category(
    name: str,
    description: Optional[str] = None,
) -> Category:
    with get_session() as session:
        category = Category(
            name=name,
            description=description,
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        return category


def update_category(
    category_id: int,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Category:
    with get_session() as session:
        category = session.get(
            Category,
            category_id
        )
        if category is None:
            raise ValueError(f'Категория {category_id} не найдена')

        if name is not None:
            category.name = name
        if description is not None:
            category.description = description
        category.to_update = datetime.utcnow()
        session.commit()
        session.refresh(category)
        return category


def get_category_by_id(
    category_id: int,
) -> Optional[Category]:
    with get_session() as session:
        category = session.get(
            Category,
            category_id
        )
        return category


def get_list_category() -> list[Category]:
    with get_session() as session:
        categories = session.query(Category).all()
        return categories
