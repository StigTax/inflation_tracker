from app.crud.base import CRUDBase
from app.models import Store


class StoreCRUD(CRUDBase[Store]):
    pass


crud = StoreCRUD(Store)
