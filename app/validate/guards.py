from __future__ import annotations

import logging
from typing import Iterable

from app.validate.exceptions import ObjectInUseError
from sqlalchemy import exists, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

logger = logging.getLogger(__name__)


def _is_referenced(
    session: Session,
    condition: ColumnElement[bool]
) -> bool:
    return bool(
        session.scalar(
            select(exists().where(condition))
        )
    )


def ensure_not_referenced(
    session: Session,
    checks: Iterable[tuple[ColumnElement[bool], str]]
) -> None:
    for condition, message in checks:
        if _is_referenced(session, condition):
            logger.warning('У объекта есть связи. Удаление запрещено!')
            raise ObjectInUseError(message)
