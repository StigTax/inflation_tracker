from __future__ import annotations

from typing import Optional, Any

from app.core.db import get_session
from app.models import Unit
from app.crud.units import crud as unit_crud


def get_unit(
    unit_id: int,
) -> Optional[Unit]:
    with get_session() as session:
        unit = unit_crud.get_or_raise(
            db=session,
            obj_id=unit_id,
        )
        return unit


def list_units(
    offset: int = 0,
    limit: int = 100,
    order_by: Optional[Any] = None,
) -> list[Unit]:
    with get_session() as session:
        units = unit_crud.list(
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
        unit = unit_crud.create(
            db=session,
            obj_in=unit,
        )
        return unit


def update_unit(
    unit_id: int,
    **fields: Any,
) -> Unit:
    with get_session() as session:
        unit = unit_crud.update(
            db=session,
            obj_id=unit_id,
            **fields,
        )
        return unit


def delete_unit(
    unit_id: int,
) -> Unit:
    with get_session() as session:
        unit = unit_crud.delete(
            db=session,
            obj_id=unit_id,
        )
        return unit
