set -euo pipefail

source venv/Scripts/activate

pyinstaller --noconfirm \
  --clean \
  --name InflationTracker \
  --onedir \
  --windowed \
  --add-data "alembic.ini;." \
  --add-data "alembic;alembic" \
  --add-data "app/data/seed;app/data/seed" \
  --collect-data matplotlib \
  --collect-data pandas \
  --collect-data numpy \
  --exclude-module matplotlib.tests \
  --exclude-module numba \
  --hidden-import=pandas.core._numba \
  --hidden-import=logging.config \
  run_gui.py