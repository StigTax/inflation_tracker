from app.crud.base import CRUDBase
from app.models import Product


class ProductCRUD(CRUDBase[Product]):
    pass


crud = ProductCRUD(Product)
