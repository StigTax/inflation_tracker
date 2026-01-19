from app.core.db import get_session
from app.crud import product_crud
from app.models.product import Product


def get_product(product_id: int) -> Product:
    with get_session() as session:
        return product_crud.get_with_relations_or_raise(
            db=session, obj_id=product_id
        )
