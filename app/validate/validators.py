import logging
import re
from datetime import date as dt_date
from typing import Optional, TypeVar, Tuple

logger = logging.getLogger(__name__)


T = TypeVar("T")


def ensure_item_exists(item: Optional[T], item_name: str, item_id: int) -> T:
    """Проверяет, что объект найден. Возвращает item (удобно для чейнинга)."""
    if item is None:
        logger.info("%s with id=%s not found", item_name, item_id)
        raise ValueError(f"{item_name} с ID {item_id} не найден.")
    return item


def validate_date_not_in_future(value: Optional[dt_date]) -> dt_date:
    """Возвращает дату, гарантируя что она не в будущем.
    Если value=None — подставляется сегодняшняя дата.
    """
    today = dt_date.today()
    if value is None:
        return today
    if value > today:
        logger.info("Purchase date in future blocked: %s > %s", value, today)
        raise ValueError("Дата покупки не может быть в будущем.")
    return value


def validate_positive_value(value: float, field_name: str) -> float:
    """Проверяет, что число > 0."""
    if value <= 0:
        logger.info("Non-positive value blocked: %s=%s", field_name, value)
        raise ValueError(f"{field_name} не может быть меньше или равной нулю.")
    return value


def _normalize_name(_str: str) -> str:
    _str = _str.strip()
    _str = re.sub(r'\s+', ' ', _str)
    return _str.casefold()


def validate_duplicate_name_item(
    value: str,
    existing_name: str
) -> str:
    if _normalize_name(value) == _normalize_name(existing_name):
        logger.warning(
            'Duplicate name blocked: %r (normalized)',
            existing_name
        )
        raise ValueError(
            f'Объект с именем "{existing_name}" уже существует.'
        )
    return value


def validate_non_empty_str(
    value: str,
    field_name: str
) -> str:
    cleaned = value.strip()
    if not cleaned:
        logger.warning(
            '%f не может быть пустым!',
            field_name
        )
        raise ValueError(
            f'{field_name} не может быть пустым.'
        )
    return cleaned


def validate_date_range(
    date_from: Optional[dt_date],
    date_to: Optional[dt_date]
) -> Tuple[Optional[dt_date], Optional[dt_date]]:
    if date_from and date_to and date_from > date_to:
        logger.warning(
            '%s не может быть больше %r',
            date_from,
            date_to
        )
        raise ValueError("date_from не может быть больше date_to.")
    return date_from, date_to


def validate_positive_int(value: int, field_name: str) -> int:
    if value <= 0:
        raise ValueError(f"{field_name} должен быть > 0.")
    return value
