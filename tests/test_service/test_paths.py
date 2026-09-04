"""Тесты построения путей окружения (app.core.paths)."""

import os
import sys
from pathlib import Path

from app.core.paths import get_app_state_dir


def test_get_app_state_dir_windows_uses_appdata(monkeypatch, tmp_path):
    fake_appdata = tmp_path / 'AppData' / 'Roaming'
    monkeypatch.setattr(os, 'name', 'nt')
    monkeypatch.setenv('APPDATA', str(fake_appdata))

    result = get_app_state_dir('TestApp')

    assert result == fake_appdata / 'TestApp'
    assert result.exists()


def test_get_app_state_dir_macos_uses_application_support(
    monkeypatch, tmp_path,
):
    monkeypatch.setattr(os, 'name', 'posix')
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)

    result = get_app_state_dir('TestApp')

    assert result == tmp_path / 'Library' / 'Application Support' / 'TestApp'



