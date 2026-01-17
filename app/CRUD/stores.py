from app.models import Store
from app.crud.base import CRUDBase


class StoreCRUD(CRUDBase[Store]):
    pass


crud = StoreCRUD(Store)
