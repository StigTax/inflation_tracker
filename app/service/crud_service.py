"""Сервисный слой для CRUD-операций."""

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
    """Проверить, помечено ли поле модели как уникальное (unique=True).

    Используется сервисным слоем, чтобы включать/выключать проверку
    уникальности имени на уровне приложения только там,
    где это действительно требуется схемой.

    Args:
        model: Класс ORM-модели SQLAlchemy.
        field: Имя ORM-атрибута (например, "name").

    Returns:
        bool: True, если у колонки стоит unique=True; иначе False.
    """
    try:
        col = getattr(model, field).property.columns[0]
        return bool(getattr(col, 'unique', False))
    except Exception:
        return False


@logged(level=logging.DEBUG)
def get_item(
    crud,
    item_id: int,
) -> Optional[ModelT]:
    """Получить объект по ID через CRUD-слой.

    Открывает сессию БД и вызывает `crud.get_or_raise(...)`.

    Args:
        crud: CRUD-объект для конкретной сущности.
        item_id: ID объекта.

    Returns:
        Optional[ModelT]: Найденный объект.

    Raises:
        ValueError: Если объект не найден (прокидывается из CRUD).
    """
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
    """Получить список объектов с пагинацией и сортировкой.

    Args:
        crud: CRUD-объект для конкретной сущности.
        offset: Смещение выборки (сколько записей пропустить).
        limit: Максимальное количество записей.
        order_by: Колонка/выражение SQLAlchemy для сортировки.

    Returns:
        list[ModelT]: Список объектов.
    """
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
    """Создать объект с прикладной валидацией и проверкой уникальности.

    Правила:
    - Если у объекта есть строковое поле `name`:
      - валидирует, что строка не пустая;
      - если поле `name` в модели помечено как unique=True,
        дополнительно проверяет уникальность имени без учёта регистра
        (через `crud.exists_by_name_ci`).
    - Если у объекта есть поля `unit` и/или `measure_type` (Unit):
      - валидирует, что они не пустые строки.

    Args:
        crud: CRUD-объект для конкретной сущности.
        obj_in: Экземпляр модели, готовый к сохранению.

    Returns:
        ModelT: Созданный объект (после commit/refresh).

    Raises:
        ValueError: Если имя/значения полей невалидны или имя не уникально.
    """

    if hasattr(
        obj_in, 'name'
    ) and isinstance(obj_in.name, str):
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
    """Обновить объект по ID с прикладной валидацией и проверкой уникальности.

    Обновляет только переданные поля
    (None не затирает значение внутри CRUDBase).
    Дополнительные правила:
    - если обновляется `name`:
      - валидирует, что строка не пустая;
      - если `name` уникальное поле, проверяет уникальность без учёта регистра
        с исключением текущего объекта.
    - если обновляются `unit`/`measure_type`, валидирует непустые строки.

    Args:
        crud: CRUD-объект для конкретной сущности.
        item_id: ID объекта для обновления.
        **fields: Поля для обновления.

    Returns:
        ModelT: Обновлённый объект.

    Raises:
        ValueError: Если данные невалидны или имя конфликтует по уникальности.
    """
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
    """Удалить объект по ID с предохранителями от удаления “используемых”
    сущностей.

    Сценарий:
    1) Открывает сессию БД.
    2) Вызывает все `guards(session, item_id)`. Guard обязан бросить
       `ObjectInUseError`, если удаление запрещено
       (например, есть связанные покупки).
    3) Удаляет объект через `crud.delete(...)`.

    IntegrityError от БД (например, FK) конвертируется в `ObjectInUseError` с
    человеческим текстом.

    Args:
        crud: CRUD-объект для конкретной сущности.
        item_id: ID удаляемого объекта.
        guards: Набор функций-проверок перед удалением.

    Returns:
        None

    Raises:
        ObjectInUseError: Если объект нельзя удалить из-за связей/ограничений.
        ValueError: Если объект не найден (прокидывается из CRUD).
    """
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
            'Нельзя удалить объект: он используется в связанных записях.'
        ) from e
