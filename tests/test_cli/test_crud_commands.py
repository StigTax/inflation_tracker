"""Сквозной тест общего CLI-механизма через сущность Category."""

import pytest
from app.cli.main import build_parser
from app.crud import category_crud
from app.service import crud_service


def test_category_crud_roundtrip_through_cli(capsys):
    parser = build_parser()

    # add
    args = parser.parse_args(
        ['category', 'add', 'Напитки', '--description', 'Соки и воды']
    )
    args.func(args)

    items = crud_service.list_items(category_crud)
    created = next((i for i in items if i.name == 'Напитки'), None)
    assert created is not None
    assert created.description == 'Соки и воды'

    # update
    args = parser.parse_args(
        ['category', 'update', str(created.id), '--description', 'Обновлено']
    )
    args.func(args)

    updated = crud_service.get_item(category_crud, created.id)
    assert updated.description == 'Обновлено'

    # list --table — печатает в stdout через PrettyTable
    args = parser.parse_args(['category', 'list', '--table'])
    args.func(args)
    assert 'Напитки' in capsys.readouterr().out

    # get
    args = parser.parse_args(['category', 'get', str(created.id)])
    args.func(args)
    assert 'Обновлено' in capsys.readouterr().out

    # delete
    args = parser.parse_args(['category', 'delete', str(created.id)])
    args.func(args)

    with pytest.raises(ValueError):
        crud_service.get_item(category_crud, created.id)
