from datetime import date
from pathlib import Path

from app.models.purchase import Purchase

APP_NAME = 'InflationTracker'

DB_URL_ENV_VAR = 'DB_URL'
DEFAULT_DB_URL = 'sqlite+pysqlite:///./inflation.db'

LOG_ROTATE_MAX_BYTES = 10 ** 6
LOG_ROTATE_BACKUP_COUNT = 5

CLI_DEFAULT_OFFSET = 0
CLI_DEFAULT_LIMIT = 100
CLI_VERBOSE_SEPARATOR_LEN = 40

BASE_DIR = Path(__file__).parent.parent
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / f'logs_to_{date.today()}.log'

LOG_FORMAT = '%(asctime)s - [%(levelname)s] - %(funcName)s: %(message)s'
DT_FORMAT = '%d.%m.%Y %H:%M:%S'

RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
RESET = '\033[0m'

DEFAULT_MAXLEN = 220
UNHANDLED = object()

MAIN_WINDOW_TITLE = 'Inflation Tracker'
MAIN_WINDOW_SIZE = (1100, 700)

DATA_MANAGER_TITLE = 'Данные'
DATA_MANAGER_SIZE = (1000, 650)

DATA_MANAGER_TABS = (
    ('Магазины', 'stores'),
    ('Категории', 'categories'),
    ('Единицы', 'units'),
    ('Продукты', 'products'),
    ('Покупки', 'purchases'),
)

MSG_TITLE_OK = 'Ок'
MSG_TITLE_ERROR = 'Ошибка'
MSG_TITLE_CHECK = 'Проверка'
MSG_TITLE_FORBIDDEN = 'Нельзя'
MSG_TITLE_CANNOT_DELETE = 'Нельзя удалить'

UI_EMPTY = '—'
UI_SELECT_TEMPLATE = '— выбери {name} —'
UI_ALL_TEMPLATE = '— все {name} —'

CHART_FIGSIZE = (6, 4)
CHART_INDEX_BASELINE = 100

ORDER_MAP = {
    'id': Purchase.id,
    'product': Purchase.product_id,
    'purchase_date': Purchase.purchase_date,
    'store': Purchase.store_id,
    'quantity': Purchase.quantity,
}
