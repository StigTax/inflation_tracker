from __future__ import annotations

import argparse

from app.cli.common import configure_db
from app.cli import categories, stores


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='inflation',
        description='CLI для трекера инфляции',
    )
    parser.add_argument(
        '--db-url',
        dest='db_url',
        default=None,
        help='DB URL (или env DB_URL)'
    )
    parser.add_argument(
        '--echo-sql',
        dest='echo_sql',
        action='store_true',
        help='Печатать SQL'
    )

    subparsers = parser.add_subparsers(dest='entity')

    categories.register_category_commands(subparsers)
    stores.register_store_commands(subparsers)
    # products.register(subparsers)
    # purchases.register(subparsers)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, 'entity', None):
        parser.print_help()
        return

    configure_db(
        getattr(
            args,
            'db_url',
            None
        ), echo_sql=getattr(args, 'echo_sql', False)
    )

    args.func(args)


if __name__ == '__main__':
    main()
