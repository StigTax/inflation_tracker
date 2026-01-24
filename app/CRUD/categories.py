"""CRUD-операции для категорий."""

from app.crud.base import CRUDBase
from app.models import Category


class CategoryCRUD(CRUDBase[Category]):
    pass


crud = CategoryCRUD(Category)
