"""CRUD-операции для покупок."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Select, func, select
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
        """Получить покупку по ID с подгруженными связями.

        Обычно этот метод нужен, чтобы:
        - подтянуть `product/category/unit` и `store` одним запросом
        (selectinload/joinedload),
          иначе ловишь “Parent instance is not bound to a Session”
          после закрытия сессии;
        - вернуть объект с вычисляемыми/нормализованными атрибутами
          (например, unit_price), если ты их формируешь на уровне
          модели/сервиса.

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

    def _build_filtered_where(
        self,
        *,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        store_id: Optional[int] = None,
        product_id: Optional[int] = None,
        product_ids: Optional[list[int]] = None,
        category_id: Optional[int] = None,
        is_promo: Optional[bool] = None,
    ) -> Select:
        """Строит SELECT(Purchase) с применёнными фильтрами.

        Без order_by/offset/limit — это общий кусок для list_filtered()
        и count_filtered(). Фильтры должны применяться идентично в обоих
        местах: если поправить условие в одном и забыть про другое,
        получишь ситуацию "на странице показано 25 из заявленных 40,
        а по факту под фильтр попадает 38" — и такой баг не поймать
        глазами, только сверкой чисел.

        Args:
            date_from: Начальная дата.
            date_to: Конечная дата.
            store_id: Идентификатор магазина.
            product_id: Идентификатор продукта.
            product_ids: Список идентификаторов продуктов.
            category_id: Идентификатор категории.
            is_promo: Фильтр по акциям.

        Returns:
            Select: Незавершённый SELECT с WHERE-условиями.
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

        return stmt

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
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list[Purchase]:
        """Универсальная выборка покупок для аналитики и UI.

        offset/limit по умолчанию не заданы (None) — это осознанно:
        аналитика (Ласпейрес) считает по ВСЕЙ отфильтрованной выборке,
        и молчаливая пагинация тут была бы багом в расчётах, а не
        оптимизацией. Постранично выбирает только GUI, явно передавая
        offset/limit.

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
            offset: Смещение выборки (для пагинации). None — без смещения.
            limit: Максимум записей (для пагинации). None — без лимита.

        Returns:
            list[Purchase]: Список покупок.
        """
        stmt = self._build_filtered_where(
            date_from=date_from,
            date_to=date_to,
            store_id=store_id,
            product_id=product_id,
            product_ids=product_ids,
            category_id=category_id,
            is_promo=is_promo,
        )

        primary_order = (
            order_by if order_by is not None else Purchase.purchase_date
        )
        # purchase_date не уникальна: несколько строк одного чека имеют
        # одинаковую дату. Вторичный ключ делает offset/limit пагинацию
        # детерминированной и не даёт строкам "прыгать" между страницами.
        stmt = stmt.order_by(primary_order, Purchase.id.asc())

        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        stmt = self._with_relations(stmt)
        return list(db.scalars(stmt).all())

    def count_filtered(
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
    ) -> int:
        """Считает, сколько покупок подходит под те же фильтры.

        Использует тот же _build_filtered_where(), что и list_filtered(),
        поэтому число всегда согласовано с тем, что реально можно
        получить постранично.

        Returns:
            int: Количество покупок, подходящих под фильтры.
        """
        stmt = self._build_filtered_where(
            date_from=date_from,
            date_to=date_to,
            store_id=store_id,
            product_id=product_id,
            product_ids=product_ids,
            category_id=category_id,
            is_promo=is_promo,
        )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        return db.scalar(count_stmt) or 0


crud = PurchaseCRUD(Purchase)
