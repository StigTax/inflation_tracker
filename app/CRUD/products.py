from app.models import Product
from app.crud.base import CRUDBase


class ProductCRUD(CRUDBase[Product]):
    pass


crud = ProductCRUD(Product)
