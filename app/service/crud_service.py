from __future__ import annotations

from typing import Any, Optional, TypeVar

import app.core.db as db

ModelT = TypeVar('ModelT')


def get_item(
    crud,
    item_id: int,
) -> Optional[ModelT]:
    with db.get_session() as session:
        item = crud.get_or_raise(
            db=session,
            obj_id=item_id,
        )
        return item


def list_items(
    crud,
    offset: int = 0,
    limit: int = 100,
    order_by: Optional[Any] = None,
) -> list[ModelT]:
    with db.get_session() as session:
        items = crud.list(
            db=session,
            offset=offset,
            limit=limit,
            order_by=order_by,
        )
        return items


def create_item(
    crud,
    obj_in: ModelT,
) -> ModelT:
    with db.get_session() as session:
        item = crud.create(
            db=session,
            obj_in=obj_in,
        )
        return item


def update_item(
    crud,
    item_id: int,
    **fields: Any,
) -> ModelT:
    with db.get_session() as session:
        item = crud.update(
            db=session,
            obj_id=item_id,
            **fields,
        )
        return item


def delete_item(
    crud,
    item_id: int,
) -> None:
    with db.get_session() as session:
        item = crud.delete(
            db=session,
            obj_id=item_id,
        )
        return item
