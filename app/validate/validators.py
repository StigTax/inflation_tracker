from typing import Optional
from datetime import date as dt_date


def ensure_item_exists(
    item: object,
    item_name: str,
    item_id: int,
) -> None:
    """Проверяет, что объект найден."""
    if item is None:
        raise ValueError(
            f'{item_name} с ID {item_id} не найден.'
        )


def validate_date_not_in_future(value: Optional[dt_date]) -> None:
    """Возвращает дату, гарантируя что она не в будущем.

    Если value=None — подставляется сегодняшняя дата.
    """
    if value is None:
        return dt_date.today()
    if value > dt_date.today():
        raise ValueError('Дата покупки не может быть в будущем.')
    return value


def validate_positive_value(
    value: float,
    field_name: str,
) -> None:
    if value <= 0:
        raise ValueError(
            f'{field_name} не может быть меньше или равной нулю.'
        )
    return value
