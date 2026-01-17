from typing import Optional

from app.core.db import get_session
from app.models import Category
from app.crud.categories import crud


def get_category(
    category_id: int,
) -> Optional[Category]:
    with get_session() as session:
        category = crud.get_or_raise(
            db=session,
            obj_id=category_id,
        )
        return category


def list_categories(
    offset: int = 0,
    limit: int = 100,
    order_by: Optional[str] = None,
) -> list[Category]:
    with get_session() as session:
        categories = crud.list(
            db=session,
            offset=offset,
            limit=limit,
            order_by=order_by,
        )
        return categories


def create_category(
    category: Category,
) -> Category:
    with get_session() as session:
        category = crud.create(
            db=session,
            obj_in=category,
        )
        return category


def update_category(
    category_id: int,
    **fields,

) -> Category:
    with get_session() as session:
        category = crud.update(
            db=session,
            obj_id=category_id,
            **fields,
        )
        return category


def delete_category(
    category_id: int,
) -> Category:
    with get_session() as session:
        category = crud.delete(
            db=session,
            obj_id=category_id,
        )
        return category
