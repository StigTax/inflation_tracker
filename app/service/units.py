from typing import Optional

from app.core.db import get_session
from app.models import Unit
from app.crud.categories import crud


def get_unit(
    unit_id: int,
) -> Optional[Unit]:
    with get_session() as session:
        unit = crud.get_or_raise(
            db=session,
            obj_id=unit_id,
        )
        return unit


def list_units(
    offset: int = 0,
    limit: int = 100,
    order_by: Optional[str] = None,
) -> list[Unit]:
    with get_session() as session:
        units = crud.list(
            db=session,
            offset=offset,
            limit=limit,
            order_by=order_by,
        )
        return units


def create_unit(
    unit: Unit,
) -> Unit:
    with get_session() as session:
        unit = crud.create(
            db=session,
            obj_in=unit,
        )
        return unit


def update_unit(
    unit_id: int,
    **fields,
) -> Unit:
    with get_session() as session:
        unit = crud.update(
            db=session,
            obj_id=unit_id,
            **fields,
        )
        return unit


def delete_unit(
    unit_id: int,
) -> Unit:
    with get_session() as session:
        unit = crud.delete(
            db=session,
            obj_id=unit_id,
        )
        return unit
