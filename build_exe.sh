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

python - <<'PY'
from pathlib import Path

source = {
    p.name
    for p in Path('alembic/versions').glob('*.py')
    if p.name != '__init__.py'
}

bundled = {
    p.name
    for p in Path('dist/InflationTracker').rglob('*.py')
    if 'alembic' in p.parts and 'versions' in p.parts
}

print('Source migrations:', sorted(source))
print('Bundled migrations:', sorted(bundled))

if source != bundled:
    missing = source - bundled
    extra = bundled - source

    raise SystemExit(
        f'Alembic bundle mismatch. '
        f'Missing={sorted(missing)}, extra={sorted(extra)}'
    )

print(f'Alembic bundle OK: {len(source)} migrations')
PY