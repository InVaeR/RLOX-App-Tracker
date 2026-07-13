"""Тесты модуля миграции."""

import json
import sqlite3
from pathlib import Path

from rlox_app_tracker.migration import (
    migrate,
    needs_migration,
)


def test_needs_migration_no_old_data(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("rlox_app_tracker.migration.OLD_APPDATA", tmp_path / "nonexistent")
    monkeypatch.setattr("rlox_app_tracker.migration.DB_PATH", tmp_path / "new" / "tracker.db")
    monkeypatch.setattr("rlox_app_tracker.migration.MIGRATION_MARKER", tmp_path / "migration" / "marker.json")
    assert not needs_migration()


def _create_sqlite_db(path: Path):
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
    conn.close()


def test_needs_migration_with_old_data(tmp_path: Path, monkeypatch):
    old_dir = tmp_path / "RusLOXPy"
    old_dir.mkdir(parents=True)
    _create_sqlite_db(old_dir / "tracker.db")
    monkeypatch.setattr("rlox_app_tracker.migration.OLD_APPDATA", old_dir)
    monkeypatch.setattr("rlox_app_tracker.migration.DB_PATH", tmp_path / "new" / "tracker.db")
    monkeypatch.setattr("rlox_app_tracker.migration.MIGRATION_MARKER", tmp_path / "migration" / "marker.json")
    assert needs_migration()


def test_migration_skipped_if_new_db_exists(tmp_path: Path, monkeypatch):
    new_dir = tmp_path / "new"
    new_dir.mkdir(parents=True)
    (new_dir / "tracker.db").write_text("existing")
    monkeypatch.setattr("rlox_app_tracker.migration.DB_PATH", new_dir / "tracker.db")
    monkeypatch.setattr("rlox_app_tracker.migration.MIGRATION_MARKER", tmp_path / "migration" / "marker.json")
    monkeypatch.setattr("rlox_app_tracker.migration.DATA_DIR", new_dir)
    monkeypatch.setattr("rlox_app_tracker.migration.CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr("rlox_app_tracker.migration.MIGRATION_DIR", tmp_path / "migration")

    assert migrate()


def test_migration_skipped_if_success_marker_exists(tmp_path: Path, monkeypatch):
    mig_dir = tmp_path / "migration"
    mig_dir.mkdir(parents=True)
    (mig_dir / "rusloxpy-1.x.json").write_text(json.dumps({"result": "success"}))
    monkeypatch.setattr("rlox_app_tracker.migration.MIGRATION_MARKER", mig_dir / "rusloxpy-1.x.json")
    monkeypatch.setattr("rlox_app_tracker.migration.DB_PATH", tmp_path / "new" / "tracker.db")
    monkeypatch.setattr("rlox_app_tracker.migration.DATA_DIR", tmp_path / "new")
    monkeypatch.setattr("rlox_app_tracker.migration.CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr("rlox_app_tracker.migration.MIGRATION_DIR", mig_dir)
    monkeypatch.setattr("rlox_app_tracker.migration.OLD_APPDATA", tmp_path / "old")

    assert migrate()


def test_migration_not_skipped_if_failed_marker(tmp_path: Path, monkeypatch):
    mig_dir = tmp_path / "migration"
    mig_dir.mkdir(parents=True)
    (mig_dir / "rusloxpy-1.x.json").write_text(json.dumps({"result": "failed"}))
    monkeypatch.setattr("rlox_app_tracker.migration.MIGRATION_MARKER", mig_dir / "rusloxpy-1.x.json")
    monkeypatch.setattr("rlox_app_tracker.migration.DB_PATH", tmp_path / "new" / "tracker.db")
    monkeypatch.setattr("rlox_app_tracker.migration.DATA_DIR", tmp_path / "new")
    monkeypatch.setattr("rlox_app_tracker.migration.CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr("rlox_app_tracker.migration.MIGRATION_DIR", mig_dir)
    monkeypatch.setattr("rlox_app_tracker.migration.OLD_APPDATA", tmp_path / "old")

    assert not migrate()


def test_migration_old_db_not_found(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("rlox_app_tracker.migration.OLD_APPDATA", tmp_path / "old")
    monkeypatch.setattr("rlox_app_tracker.migration.DB_PATH", tmp_path / "new" / "tracker.db")
    monkeypatch.setattr("rlox_app_tracker.migration.MIGRATION_MARKER", tmp_path / "migration" / "marker.json")
    monkeypatch.setattr("rlox_app_tracker.migration.DATA_DIR", tmp_path / "new")
    monkeypatch.setattr("rlox_app_tracker.migration.CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr("rlox_app_tracker.migration.MIGRATION_DIR", tmp_path / "migration")

    result = migrate()
    assert not result


def test_migration_config(tmp_path: Path, monkeypatch):
    old_dir = tmp_path / "RusLOXPy"
    old_dir.mkdir(parents=True)
    old_db = old_dir / "tracker.db"
    _create_sqlite_db(old_db)
    old_cfg = old_dir / "config.json"
    old_cfg.write_text(json.dumps({"idle_threshold": 600, "poll_interval": 2.0}))

    new_dir = tmp_path / "new"
    new_dir.mkdir(parents=True)
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    mig_dir = tmp_path / "migration"
    mig_dir.mkdir(parents=True)

    monkeypatch.setattr("rlox_app_tracker.migration.OLD_APPDATA", old_dir)
    monkeypatch.setattr("rlox_app_tracker.migration.DB_PATH", new_dir / "tracker.db")
    monkeypatch.setattr("rlox_app_tracker.migration.APP_CONFIG_PATH", config_dir / "app.json")
    monkeypatch.setattr("rlox_app_tracker.migration.MIGRATION_MARKER", mig_dir / "rusloxpy-1.x.json")
    monkeypatch.setattr("rlox_app_tracker.migration.DATA_DIR", new_dir)
    monkeypatch.setattr("rlox_app_tracker.migration.CONFIG_DIR", config_dir)
    monkeypatch.setattr("rlox_app_tracker.migration.MIGRATION_DIR", mig_dir)

    result = migrate()
    assert result
    assert (new_dir / "tracker.db").exists()
    assert (config_dir / "app.json").exists()
    assert (mig_dir / "rusloxpy-1.x.json").exists()
