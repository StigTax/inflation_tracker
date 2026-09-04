"""Тесты резолва DB_URL (app.core.settings.get_db_url и load_env_once)."""

import os
import sys

import pytest
from app.core import settings
from app.core.paths import build_sqlite_url, get_default_db_path


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch, tmp_path):
    """Полная изоляция от реального окружения разработчика.

    get_db_url() читает os.environ, Path.cwd() и модульный кэш _ENV_LOADED —
    без сброса тесты начинают зависеть от порядка запуска и от того,
    что лежит в реальной рабочей директории/venv разработчика.
    """
    monkeypatch.delenv('DB_URL', raising=False)
    monkeypatch.setattr(settings, '_ENV_LOADED', False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'fake_python'))
    yield


def test_get_db_url_override_wins_over_everything(monkeypatch):
    monkeypatch.setenv('DB_URL', 'sqlite+pysqlite:///from-env.db')

    url = settings.get_db_url(override='sqlite+pysqlite:///explicit.db')

    assert url == 'sqlite+pysqlite:///explicit.db'


def test_get_db_url_falls_back_to_env_var(monkeypatch):
    monkeypatch.setenv('DB_URL', 'sqlite+pysqlite:///from-env.db')

    url = settings.get_db_url()

    assert url == 'sqlite+pysqlite:///from-env.db'


def test_get_db_url_uses_local_file_in_dev_mode_when_present(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    (tmp_path / 'inflation.db').touch()

    url = settings.get_db_url()

    assert url == build_sqlite_url(tmp_path / 'inflation.db')


def test_get_db_url_ignores_local_file_when_frozen(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    (tmp_path / 'inflation.db').touch()

    url = settings.get_db_url()

    assert url == build_sqlite_url(get_default_db_path())


def test_get_db_url_falls_back_to_state_dir_when_nothing_else_set(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)

    url = settings.get_db_url()

    assert url == build_sqlite_url(get_default_db_path())


def test_load_env_once_reads_env_file_from_cwd(tmp_path):
    (tmp_path / '.env').write_text(
        'DB_URL=sqlite+pysqlite:///from-dotenv.db\n'
    )

    settings.load_env_once()

    assert os.environ.get('DB_URL') == 'sqlite+pysqlite:///from-dotenv.db'


def test_load_env_once_only_loads_once(tmp_path):
    (tmp_path / '.env').write_text(
        'DB_URL=sqlite+pysqlite:///from-dotenv.db\n'
    )
    settings.load_env_once()

    (tmp_path / '.env').write_text('DB_URL=sqlite+pysqlite:///changed.db\n')
    settings.load_env_once()

    assert os.environ.get('DB_URL') == 'sqlite+pysqlite:///from-dotenv.db'
