"""CRUD-операции для покупок."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models import Product, Purchase
from app.validate.validators import ensure_item_exists


class PurchaseCRUD(CRUDBase[Purchase]):
    def __init__(self, model: type[Purchase]):
        super().__init__(model)

    def _with_relations(self, stmt):
        return stmt.options(
            selectinload(Purchase.store),
            selectinload(Purchase.product).selectinload(Product.unit),
            selectinload(Purchase.product).selectinload(Product.category),
        )

    def get_with_normal_attr_or_raise(
        self,
        db: Session,
        obj_id: int,
    ) -> Purchase:
        """Получить покупку по ID с подгруженными связями и нормализованными полями.

        Обычно этот метод нужен, чтобы:
        - подтянуть `product/category/unit` и `store` одним запросом (selectinload/joinedload),
          иначе ловишь “Parent instance is not bound to a Session” после закрытия сессии;
        - вернуть объект с вычисляемыми/нормализованными атрибутами (например, unit_price),
          если ты их формируешь на уровне модели/сервиса.

        Args:
            session: Активная SQLAlchemy-сессия.
            purchase_id: ID покупки.

        Returns:
            Purchase: Покупка со связями.

        Raises:
            ValueError: Если покупка не найдена.
        """
        stmt = self._with_relations(
            select(Purchase).where(Purchase.id == obj_id),
        )
        obj = db.scalars(stmt).first()
        ensure_item_exists(obj, self.model.__name__, obj_id)
        return obj

    def list(
        self,
        db: Session,
        *,
        offset=0,
        limit=100,
        order_by=None,
        is_promo: Optional[bool] = None
    ) -> list[Purchase]:
        stmt = select(Purchase)
        if is_promo is not None:
            stmt = stmt.where(Purchase.is_promo == is_promo)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = self._with_relations(stmt.offset(offset).limit(limit))
        return list(db.scalars(stmt).all())

    def get_purchase_by_store(
        self,
        db: Session,
        store_id: int,
        is_promo: Optional[bool] = None,
    ) -> list[Purchase]:
        stmt = select(Purchase).where(Purchase.store_id == store_id)

        if is_promo is not None:
            stmt = stmt.where(Purchase.is_promo == is_promo)

        stmt = self._with_relations(stmt.order_by(Purchase.purchase_date))
        return list(db.scalars(stmt).all())

    def get_purchase_by_product(
        self,
        db: Session,
        product_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        is_promo: Optional[bool] = None,
    ) -> list[Purchase]:
        stmt = select(Purchase).where(Purchase.product_id == product_id)

        if is_promo is not None:
            stmt = stmt.where(Purchase.is_promo == is_promo)

        if date_from is not None:
            stmt = stmt.where(Purchase.purchase_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Purchase.purchase_date <= date_to)

        stmt = self._with_relations(stmt.order_by(Purchase.purchase_date))
        return list(db.scalars(stmt).all())

    def list_filtered(
        self,
        db: Session,
        *,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        store_id: Optional[int] = None,
        product_id: Optional[int] = None,
        product_ids: Optional[list[int]] = None,
        category_id: Optional[int] = None,
        is_promo: Optional[bool] = None,
        order_by=None,
    ) -> list[Purchase]:
        """Универсальная выборка покупок для аналитики.

        Args:
            db: Сессия SQLAlchemy.
            date_from: Начальная дата.
            date_to: Конечная дата.
            store_id: Идентификатор магазина.
            product_id: Идентификатор продукта.
            product_ids: Список идентификаторов продуктов.
            category_id: Идентификатор категории.
            is_promo: Фильтр по акциям.
            order_by: Поле сортировки.

        Returns:
            list[Purchase]: Список покупок.
        """
        stmt = select(Purchase)

        if category_id is not None:
            stmt = stmt.join(
                Purchase.product
            ).where(
                Product.category_id == category_id
            )

        if store_id is not None:
            stmt = stmt.where(Purchase.store_id == store_id)

        if product_id is not None:
            stmt = stmt.where(Purchase.product_id == product_id)

        if product_ids:
            stmt = stmt.where(Purchase.product_id.in_(product_ids))

        if is_promo is not None:
            stmt = stmt.where(Purchase.is_promo == is_promo)

        if date_from is not None:
            stmt = stmt.where(Purchase.purchase_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Purchase.purchase_date <= date_to)

        stmt = stmt.order_by(order_by or Purchase.purchase_date)
        stmt = self._with_relations(stmt)
        return list(db.scalars(stmt).all())


crud = PurchaseCRUD(Purchase)
