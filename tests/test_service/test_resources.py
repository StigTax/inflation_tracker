"""Тесты резолва базовой директории ресурсов (app/core/resources.py)."""

import sys

from app.core.resources import resource_base_dir


def test_dev_mode_returns_project_root(monkeypatch):
    """Без sys._MEIPASS — это корень репозитория (3 уровня вверх от файла)."""
    monkeypatch.delattr(sys, '_MEIPASS', raising=False)

    base = resource_base_dir()

    assert (base / 'alembic.ini').exists()
    assert (base / 'app' / 'data' / 'seed').is_dir()


def test_frozen_mode_uses_meipass(monkeypatch, tmp_path):
    """Внутри PyInstaller-сборки берём именно sys._MEIPASS, а не cwd."""
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)

    assert resource_base_dir() == tmp_path.resolve()
