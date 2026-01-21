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


def validate_date_range(
    date_from: Optional[dt_date],
    date_to: Optional[dt_date]
) -> Tuple[Optional[dt_date], Optional[dt_date]]:
    if date_from and date_to and date_from > date_to:
        raise ValueError("date_from не может быть больше date_to.")
    return date_from, date_to


def validate_positive_value(value: float, field_name: str) -> float:
    """Проверяет, что число > 0."""
    if value <= 0:
        logger.info("Non-positive value blocked: %s=%s", field_name, value)
        raise ValueError(f"{field_name} не может быть меньше или равной нулю.")
    return value


def clean_text(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_name(s: str) -> str:
    # для сравнения (уникальность без учета регистра)
    return clean_text(s).casefold()


def validate_non_empty_str(value: str, field_name: str) -> str:
    cleaned = clean_text(value)
    if not cleaned:
        raise ValueError(f"{field_name} не может быть пустым.")
    return cleaned


def validate_unique_name(value: str, exists: bool) -> str:
    if exists:
        raise ValueError(f"Объект с именем '{value}' уже существует.")
    return value
