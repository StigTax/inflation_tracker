from app.models import Unit
from app.crud.base import CRUDBase


class UnitCRUD(CRUDBase[Unit]):
    pass


crud = UnitCRUD(Unit)
