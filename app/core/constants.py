'''Константы приложения.'''

from datetime import date
from pathlib import Path

from app.models.purchase import Purchase

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

ORDER_MAP = {
    'id': Purchase.id,
    'product': Purchase.product_id,
    'purchase_date': Purchase.purchase_date,
    'store': Purchase.store_id,
    'quantity': Purchase.quantity,
}

DEFAULT_MAXLEN = 220
UNHANDLED = object()
