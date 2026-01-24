"""CRUD-операции для единиц измерения."""

from app.crud.base import CRUDBase
from app.models import Unit


class UnitCRUD(CRUDBase[Unit]):
    pass


crud = UnitCRUD(Unit)
