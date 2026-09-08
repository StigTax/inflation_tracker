"""Тесты чтения CSV с сид-данными (app/core/seed_csv.py).

Модуль намеренно не трогает ORM/БД — тестируем чистую функцию на
временных файлах, без фикстур engine/session из conftest.py.
"""

from pathlib import Path

import pytest
from app.core.seed_csv import SeedCsvError, read_seed_rows


def _write_csv(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding='utf-8')
    return path


def test_reads_valid_rows(tmp_path):
    path = _write_csv(
        tmp_path, 'categories.csv',
        'name,description\nЕда,Продукты питания\nНапитки,\n',
    )

    rows = read_seed_rows(
        path, required_columns=['name', 'description'], key_column='name'
    )

    assert rows == [
        {'name': 'Еда', 'description': 'Продукты питания'},
        {'name': 'Напитки', 'description': ''},
    ]


def test_strips_surrounding_whitespace(tmp_path):
    path = _write_csv(
        tmp_path, 'stores.csv',
        'name,description\n  Пятёрочка  , рядом с домом \n',
    )

    rows = read_seed_rows(
        path, required_columns=['name', 'description'], key_column='name'
    )

    assert rows == [{'name': 'Пятёрочка', 'description': 'рядом с домом'}]


def test_skips_rows_with_empty_key(tmp_path):
    path = _write_csv(
        tmp_path, 'categories.csv',
        'name,description\nA,x\n,\nB,y\n',
    )

    rows = read_seed_rows(
        path, required_columns=['name', 'description'], key_column='name'
    )

    assert [r['name'] for r in rows] == ['A', 'B']


def test_duplicate_key_raises(tmp_path):
    path = _write_csv(
        tmp_path, 'categories.csv',
        'name,description\nA,x\nA,y\n',
    )

    with pytest.raises(SeedCsvError, match='повторяющееся значение'):
        read_seed_rows(
            path, required_columns=['name', 'description'], key_column='name'
        )


def test_missing_required_column_raises(tmp_path):
    path = _write_csv(tmp_path, 'categories.csv', 'name\nA\n')

    with pytest.raises(SeedCsvError, match='не хватает колонок'):
        read_seed_rows(
            path, required_columns=['name', 'description'], key_column='name'
        )


def test_missing_file_raises(tmp_path):
    with pytest.raises(SeedCsvError, match='не найден'):
        read_seed_rows(
            tmp_path / 'nope.csv',
            required_columns=['name'],
            key_column='name',
        )
