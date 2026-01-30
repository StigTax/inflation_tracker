set -euo pipefail

source venv/Scripts/activate

pyinstaller --noconfirm \
  --clean \
  --name InflationTracker \
  --onedir \
  --windowed \
  --add-data "alembic.ini;." \
  --add-data "alembic;alembic" \
  --collect-data matplotlib \
  --collect-data pandas \
  --collect-data numpy \
  --exclude-module matplotlib.tests \
  --exclude-module numba \
  --hidden-import=pandas.core._numba \
  run_gui.py