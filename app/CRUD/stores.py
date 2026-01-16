from typing import Optional
from datetime import datetime

from app.core.db import get_session
from app.models import Store


def create_store(
    name: str,
    description: Optional[str] = None,
) -> Store:
    with get_session() as session:
        store = Store(
            name=name,
            description=description,
        )
        session.add(store)
        session.commit()
        session.refresh(store)
        return store


def update_store(
    store_id: int,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Store:
    with get_session() as session:
        store = session.get(
            Store,
            store_id
        )
        if store is None:
            raise ValueError(f'Магазин {store_id} не найден')

        if name is not None:
            store.name = name
        if description is not None:
            store.description = description
        store.to_update = datetime.utcnow()
        session.commit()
        session.refresh(store)
        return store


def get_store_by_id(
    store_id: int,
) -> Optional[Store]:
    with get_session() as session:
        store = session.get(
            Store,
            store_id
        )
        return store


def get_list_store() -> list[Store]:
    with get_session() as session:
        stores = session.query(Store).all()
        return stores
