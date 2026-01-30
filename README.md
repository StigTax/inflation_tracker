# Трекер для отслеживания инфляции

Небольшое приложение для учета покупок и анализа динамики цен.
В проекте есть CLI для CRUD-операций и GUI на PyQt6.

## Локальное развертывание

### Требования
- Python 3.9+

### Установка зависимостей
Рекомендуемый способ для разработки:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### База данных и конфигурация
По умолчанию приложение использует SQLite и само применяет миграции при
первом запуске.
Источник БД выбирается в следующем порядке:
1) `--db-url` (CLI) или `DB_URL` (окружение),
2) `./inflation.db` в корне проекта (если файл существует),
3) пользовательский каталог состояния (APPDATA/`~/.local/state` и т.п.).

Можно положить `DB_URL` в `.env` в корне проекта — он будет подхвачен
автоматически.

Пример для Linux/macOS:
```bash
export DB_URL="sqlite+pysqlite:///$(pwd)/inflation.db"
```

### Запуск
CLI:
```bash
python -m app.cli.main --help
```

GUI (нужны зависимости из requirements.txt, включая PyQt6):
```bash
python -m app.gui.main
```

## Примеры CLI
Базовый сценарий: создать справочники, затем покупки.

```bash
# Категории
python -m app.cli.main category add "Еда" --description "Продукты питания"
python -m app.cli.main category list --table

# Единицы измерения
python -m app.cli.main units add "кг" --measure-type "Вес"
python -m app.cli.main units list --table

# Магазины
python -m app.cli.main store add "Пятёрочка" --description "Возле дома"
python -m app.cli.main store list --table

# Продукты
python -m app.cli.main product add "Яблоки" --category-id 1 --unit-id 1
python -m app.cli.main product list --table

# Покупки
python -m app.cli.main purchase add \
  --date 2025-01-20 \
  --product-id 1 \
  --store-id 1 \
  --quantity 2 \
  --total-price 199.90 \
  --promo \
  --promo-type discount \
  --regular-unit-price 129.90

python -m app.cli.main purchase list --table

# Фильтрация покупок по продукту и датам
python -m app.cli.main purchase list \
  --product-id 1 \
  --from-date 2025-01-01 \
  --to-date 2025-01-31 \
  --table
```

Полезные опции:
- `--db-url` и `--echo-sql` доступны для всех CLI-команд.
- `list` поддерживает `--full` (key: value) и `--table` (таблица).

## Скриншоты графического интерфейса
_Заготовка для будущих скриншотов GUI:_

![Главный экран](docs\screenshots/main.png)
![Список магазинов](docs\screenshots/store_crud.png)
![Список категорий](docs\screenshots/category_crud.png)
![Список единиц измерений](docs\screenshots/unit_crud.png)
![Список продуктов](docs\screenshots/product_crud.png)
![Список покупок](docs\screenshots/purchase_crud.png)
