from app.models import Category
from app.crud.base import CRUDBase


class CategoryCRUD(CRUDBase[Category]):
    pass


crud = CategoryCRUD(Category)
