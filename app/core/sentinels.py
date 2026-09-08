"""Служебные маркеры для различения отсутствующих и пустых значений."""

from __future__ import annotations


class UnsetType:
    """Маркер: аргумент не был передан вызывающей стороной."""

    __slots__ = ()

    def __repr__(self) -> str:
        return 'UNSET'


UNSET = UnsetType()
