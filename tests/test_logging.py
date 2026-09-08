from __future__ import annotations

import io
import logging
import sys

import pytest
from app.core.config_log import configure_logging
from app.core.migrations import upgrade_db
from app.logging import logged


def test_debug_goes_to_console_but_not_file(tmp_path, monkeypatch):
    stream = io.StringIO()
    monkeypatch.setattr(sys, 'stderr', stream)

    log_file = configure_logging(
        log_level=logging.INFO,
        console_level=logging.DEBUG,
        enable_console=True,
        log_dir=tmp_path,
    )

    logger = logging.getLogger('tests.logging')
    logger.debug('debug-marker')
    logger.info('info-marker')

    console = stream.getvalue()
    file_text = log_file.read_text(encoding='utf-8')

    assert 'debug-marker' in console
    assert 'info-marker' in console
    assert 'debug-marker' not in file_text
    assert 'info-marker' in file_text


def test_production_file_contains_info_and_above(tmp_path):
    log_file = configure_logging(
        log_level=logging.INFO,
        enable_console=False,
        log_dir=tmp_path,
    )

    logger = logging.getLogger('tests.logging.production')
    logger.debug('debug-hidden')
    logger.info('info-visible')
    logger.warning('warning-visible')

    file_text = log_file.read_text(encoding='utf-8')

    assert 'debug-hidden' not in file_text
    assert 'info-visible' in file_text
    assert 'warning-visible' in file_text


def test_logged_value_error_is_warning_without_traceback(tmp_path):
    log_file = configure_logging(
        log_level=logging.DEBUG,
        enable_console=False,
        log_dir=tmp_path,
    )

    @logged()
    def fail_validation() -> None:
        raise ValueError('Некорректное значение')

    with pytest.raises(ValueError, match='Некорректное значение'):
        fail_validation()

    file_text = log_file.read_text(encoding='utf-8')
    assert 'WARNING' in file_text
    assert 'Некорректное значение' in file_text
    assert 'Traceback' not in file_text


def test_alembic_does_not_replace_application_file_handler(tmp_path):
    log_file = configure_logging(
        log_level=logging.INFO,
        enable_console=False,
        log_dir=tmp_path / 'logs',
    )
    logger = logging.getLogger('tests.logging.alembic')
    logger.info('before-migration')

    db_path = tmp_path / 'logging.sqlite'
    upgrade_db(f'sqlite+pysqlite:///{db_path.as_posix()}')

    logger.info('after-migration')
    file_text = log_file.read_text(encoding='utf-8')

    assert 'before-migration' in file_text
    assert 'after-migration' in file_text
    assert any(
        isinstance(handler, logging.FileHandler)
        for handler in logging.getLogger().handlers
    )
