from __future__ import annotations

import argparse
import logging
import sys

from app.cli import categories, products, purchases, stores, units
from app.cli.common import configure_db
from app.core.config_log import configure_logging

logger = logging.getLogger(__name__)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='inflation',
        description='CLI для тестирования CRUD слоёв проекта.',
    )
    parser.add_argument(
        '--db-url',
        dest='db_url',
        default=None,
        help='DB URL (или env DB_URL)',
    )
    parser.add_argument(
        '--echo-sql',
        dest='echo_sql',
        action='store_true',
        help='Печатать SQL',
    )

    subparsers = parser.add_subparsers(
        dest='entity', required=True
    )

    categories.register_category_commands(subparsers)
    stores.register_store_commands(subparsers)
    units.register_unit_commands(subparsers)
    products.register_product_commands(subparsers)
    purchases.register_purchase_commands(subparsers)

    return parser


def main():
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()
    configure_db(db_url=args.db_url, echo_sql=args.echo_sql)

    try:
        args.func(args)
    except Exception as e:
        logger.error(
            'CLI command failed: entity=%s, action=%s',
            getattr(args, 'entity', None),
            getattr(args, 'action', None),
        )
        raise SystemExit(e)


if __name__ == '__main__':
    main()
