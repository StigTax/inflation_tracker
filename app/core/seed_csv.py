"""Чтение CSV с начальными справочными данными (категории/единицы/магазины).

Специально не импортирует app.models: этим модулем пользуется Alembic-
миграция, а миграции обязаны оставаться рабочими и годы спустя после
того, как модели поменяются. Поэтому на выходе — обычные dict, а не
ORM-объекты; вставку в БД делает сама миграция через op.bulk_insert().
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence


class SeedCsvError(ValueError):
    """Файл сид-данных повреждён или не соответствует ожидаемой схеме."""


def read_seed_rows(
    path: Path,
    *,
    required_columns: Sequence[str],
    key_column: str,
) -> list[dict[str, str]]:
    """Прочитать CSV с сид-данными в список словарей.

    Правила:
    - Пустые строки и строки с пустым `key_column` пропускаются молча —
      это удобно, чтобы можно было оставлять "разделительные" пустые
      строки в CSV для читаемости, не переживая за падение импорта.
    - Значения обрезаются от пробелов по краям (частая опечатка при
      ручном редактировании CSV в Excel/Google Sheets).
    - Дубликаты по `key_column` внутри одного файла — ошибка: тихо
      оставлять только последний/первый повтор означало бы молча
      терять данные, которые человек явно(!) прописал дважды.

    Args:
        path: Путь к CSV-файлу (с заголовком в первой строке).
        required_columns: Колонки, которые обязаны быть в заголовке.
        key_column: Колонка, по которой проверяются пустые строки
            и дубликаты (обычно 'name' или другой естественный ключ).

    Returns:
        list[dict[str, str]]: Строки файла в виде словарей column -> value.

    Raises:
        SeedCsvError: Файл не найден, нет обязательной колонки в
            заголовке, или найден дубликат по key_column.
    """
    if not path.exists():
        raise SeedCsvError(f'Файл сид-данных не найден: {path}')

    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []

        missing = [c for c in required_columns if c not in header]
        if missing:
            raise SeedCsvError(
                f'{path.name}: в заголовке не хватает колонок {missing} '
                f'(есть: {header})'
            )

        rows: list[dict[str, str]] = []
        seen_keys: set[str] = set()

        for raw_row in reader:
            row = {
                col: (raw_row.get(col) or '').strip()
                for col in required_columns
            }
            key = row[key_column]
            if not key:
                continue

            if key in seen_keys:
                raise SeedCsvError(
                    f"{path.name}: повторяющееся значение "
                    f"'{key_column}'='{key}' — проверь файл."
                )
            seen_keys.add(key)
            rows.append(row)

        return rows
