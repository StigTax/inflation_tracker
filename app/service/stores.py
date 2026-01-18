from __future__ import annotations

from typing import Any, Optional

from app.core.db import get_session
from app.crud.stores import crud as store_crud
from app.models import Store


def get_store(
    store_id: int,
) -> Optional[Store]:
    with get_session() as session:
        store = store_crud.get_or_raise(
            db=session,
            obj_id=store_id,
        )
        return store


def list_stores(
    offset: int = 0,
    limit: int = 100,
    order_by: Optional[Any] = None,
) -> list[Store]:
    with get_session() as session:
        stores = store_crud.list(
            db=session,
            offset=offset,
            limit=limit,
            order_by=order_by,
        )
        return stores


def create_store(
    store: Store,
) -> Store:
    with get_session() as session:
        store = store_crud.create(
            db=session,
            obj_in=store,
        )
        return store


def update_store(
    store_id: int,
    **fields: Any,
) -> Store:
    with get_session() as session:
        store = store_crud.update(
            db=session,
            obj_id=store_id,
            **fields,
        )
        return store


def delete_store(
    store_id: int,
) -> Store:
    with get_session() as session:
        store = store_crud.delete(
            db=session,
            obj_id=store_id,
        )
        return store
