"""Добавлены флаги удаления для связанных полей

Revision ID: 61f0a5cec42e
Revises: 16269c5dd309
Create Date: 2026-01-22 02:41:37.123639

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models import Product, Purchase, Store, Unit, Category


# revision identifiers, used by Alembic.
revision: str = '61f0a5cec42e'
down_revision: Union[str, Sequence[str], None] = '16269c5dd309'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table(
        "product",
        schema=None,
        naming_convention=NAMING_CONVENTION,
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint("fk_product_unit_id_unit", type_="foreignkey")
        batch_op.drop_constraint("fk_product_category_id_category", type_="foreignkey")

        # создаём новые с ondelete
        batch_op.create_foreign_key(
            "fk_product_unit_id_unit",
            "unit",
            ["unit_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_product_category_id_category",
            "category",
            ["category_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table(
        "purchase",
        schema=None,
        naming_convention=NAMING_CONVENTION,
        recreate="always",
    ) as batch_op:
        batch_op.alter_column(
            "store_id",
            existing_type=sa.INTEGER(),
            nullable=False,
        )

        batch_op.drop_constraint("fk_purchase_product_id_product", type_="foreignkey")
        batch_op.drop_constraint("fk_purchase_store_id_store", type_="foreignkey")

        batch_op.create_foreign_key(
            "fk_purchase_product_id_product",
            "product",
            ["product_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_purchase_store_id_store",
            "store",
            ["store_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table(
        "purchase",
        schema=None,
        naming_convention=NAMING_CONVENTION,
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint("fk_purchase_product_id_product", type_="foreignkey")
        batch_op.drop_constraint("fk_purchase_store_id_store", type_="foreignkey")

        batch_op.create_foreign_key(
            "fk_purchase_product_id_product",
            "product",
            ["product_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_purchase_store_id_store",
            "store",
            ["store_id"],
            ["id"],
        )

        batch_op.alter_column(
            "store_id",
            existing_type=sa.INTEGER(),
            nullable=True,
        )

    with op.batch_alter_table(
        "product",
        schema=None,
        naming_convention=NAMING_CONVENTION,
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint("fk_product_unit_id_unit", type_="foreignkey")
        batch_op.drop_constraint("fk_product_category_id_category", type_="foreignkey")

        batch_op.create_foreign_key(
            "fk_product_unit_id_unit",
            "unit",
            ["unit_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_product_category_id_category",
            "category",
            ["category_id"],
            ["id"],
        )
