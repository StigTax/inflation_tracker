"""Простой in-memory кэш справочников для GUI.

Зачем: категории/единицы/продукты/магазины меняются редко, а читаются
из каждого диалога и каждой вкладки по новой. Кэш живёт в памяти процесса
GUI и сбрасывается явно после create/update/delete через invalidate().
"""

from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar('T')

_cache: dict[str, list] = {}


def get_cached(key: str, loader: Callable[[], list[T]]) -> list[T]:
    """Вернуть закэшированный список, при первом обращении — загрузить.

    Args:
        key: Ключ кэша (например, 'categories', 'units').
        loader: Функция без аргументов, которая реально ходит в БД.

    Returns:
        list[T]: Закэшированные объекты.
    """
    if key not in _cache:
        _cache[key] = loader()
    return _cache[key]


def invalidate(*keys: str) -> None:
    """Сбросить кэш по ключам. Без аргументов — не делает ничего.

    Args:
        *keys: Ключи, которые нужно сбросить.
    """
    for k in keys:
        _cache.pop(k, None)


def invalidate_all() -> None:
    """Сбросить весь кэш целиком (пригодится, например, при импорте данных)."""
    _cache.clear()
