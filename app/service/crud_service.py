from __future__ import annotations

import logging
from typing import Any, Optional, TypeVar

from app.core.db import get_session
from app.logging import logged

ModelT = TypeVar('ModelT')


@logged(level=logging.DEBUG)
def get_item(
    crud,
    item_id: int,
) -> Optional[ModelT]:
    with get_session() as session:
        item = crud.get_or_raise(
            db=session,
            obj_id=item_id,
        )
        return item


@logged(level=logging.DEBUG)
def list_items(
    crud,
    offset: int = 0,
    limit: int = 100,
    order_by: Optional[Any] = None,
) -> list[ModelT]:
    with get_session() as session:
        items = crud.list(
            db=session,
            offset=offset,
            limit=limit,
            order_by=order_by,
        )
        return items


@logged(level=logging.INFO, skip_empty=True)
def create_item(
    crud,
    obj_in: ModelT,
) -> ModelT:
    with get_session() as session:
        item = crud.create(
            db=session,
            obj_in=obj_in,
        )
        return item


@logged(level=logging.INFO, skip_empty=True)
def update_item(
    crud,
    item_id: int,
    **fields: Any,
) -> ModelT:
    with get_session() as session:
        item = crud.update(
            db=session,
            obj_id=item_id,
            **fields,
        )
        return item


@logged(level=logging.INFO)
def delete_item(
    crud,
    item_id: int,
) -> None:
    with get_session() as session:
        item = crud.delete(
            db=session,
            obj_id=item_id,
        )
        return item
