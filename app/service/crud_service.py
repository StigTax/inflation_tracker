from __future__ import annotations

import logging
from typing import Any, Callable, Iterable, Optional, TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.logging import logged
from app.validate.exceptions import ObjectInUseError
from app.validate.validators import (
    validate_non_empty_str,
    validate_unique_name,
)

ModelT = TypeVar('ModelT')
DeleteGuard = Callable[[Session, int], None]


def _column_unique(model: type, field: str) -> bool:
    try:
        col = getattr(model, field).property.columns[0]
        return bool(getattr(col, "unique", False))
    except Exception:
        return False


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
    if hasattr(obj_in, 'name') and isinstance(obj_in.name, str):
        obj_in.name = validate_non_empty_str(
            obj_in.name,
            'Название'
        )

        if _column_unique(
            obj_in.__class__,
            'name'
        ):
            with get_session() as session:
                exists = crud.exists_by_name_ci(
                    db=session,
                    field='name',
                    name=obj_in.name
                )
                validate_unique_name(
                    obj_in.name, exists
                )
                return crud.create(
                    db=session, obj_in=obj_in
                )

    if hasattr(
        obj_in, 'unit'
    ) and isinstance(obj_in.unit, str):
        obj_in.unit = validate_non_empty_str(
            obj_in.unit,
            'Единица измерения'
        )

    if hasattr(
        obj_in,
        'measure_type'
    ) and isinstance(obj_in.measure_type, str):
        obj_in.measure_type = validate_non_empty_str(
            obj_in.measure_type,
            'Тип единицы измерения'
        )

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
    if 'name' in fields and fields['name'] is not None:
        fields['name'] = validate_non_empty_str(fields['name'], 'Название')

        if _column_unique(crud.model, 'name'):
            with get_session() as session:
                exists = crud.exists_by_name_ci(
                    db=session,
                    field='name',
                    name=fields['name'],
                    exclude_id=item_id
                )
                validate_unique_name(fields['name'], exists)
                return crud.update(db=session, obj_id=item_id, **fields)

    if 'unit' in fields and fields['unit'] is not None:
        fields['unit'] = validate_non_empty_str(
            fields['unit'],
            'Единица измерения'
        )

    if 'measure_type' in fields and fields['measure_type'] is not None:
        fields['measure_type'] = validate_non_empty_str(
            fields['measure_type'],
            'Тип единицы измерения'
        )
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
    *,
    guards: Iterable[DeleteGuard] = (),
) -> None:
    try:
        with get_session() as session:
            for guard in guards:
                guard(session, item_id)

            crud.delete(
                db=session,
                obj_id=item_id,
            )
    except IntegrityError as e:
        raise ObjectInUseError(
            "Нельзя удалить объект: он используется в связанных записях."
        ) from e
