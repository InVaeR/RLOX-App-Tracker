"""
Миграция данных из старого RusLOXPy в RLOX App Tracker.
"""

import json
import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from rlox_app_tracker.paths import APP_CONFIG_PATH, CONFIG_DIR, DATA_DIR, DB_PATH, MIGRATION_DIR

logger = logging.getLogger(__name__)

OLD_APPDATA = Path.home() / "AppData" / "Roaming" / "RusLOXPy"
MIGRATION_MARKER = MIGRATION_DIR / "rusloxpy-1.x.json"


def _get_old_db_path() -> Optional[Path]:
    db = OLD_APPDATA / "tracker.db"
    return db if db.exists() else None


def _get_old_config_path() -> Optional[Path]:
    cfg = OLD_APPDATA / "config.json"
    return cfg if cfg.exists() else None


def _checkpoint_old_db(db_path: Path):
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
    except Exception as e:
        logger.warning("Checkpoint старой БД не удался: %s", e)


def _copy_db(old_path: Path) -> bool:
    backup_path = MIGRATION_DIR / "rusloxpy-tracker.db.backup"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(str(old_path), str(backup_path))
        logger.info("Резервная копия старой БД: %s", backup_path)
        shutil.copy2(str(old_path), str(DB_PATH))
        for ext in ("-wal", "-shm"):
            src = old_path.with_name(old_path.name + ext)
            if src.exists():
                shutil.copy2(str(src), str(DB_PATH.parent / (DB_PATH.name + ext)))
        logger.info("БД мигрирована: %s -> %s", old_path, DB_PATH)
        return True
    except OSError as e:
        logger.error("Ошибка копирования БД: %s", e)
        return False


def _migrate_config(old_path: Path) -> bool:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(old_path.read_text(encoding="utf-8"))
        new_config = {
            "idle_threshold": data.get("idle_threshold", 300),
            "poll_interval": data.get("poll_interval", 1.5),
            "save_window_titles": data.get("save_window_titles", True),
            "minimize_to_tray": data.get("minimize_to_tray", True),
            "check_updates_on_start": data.get("check_updates_on_start", True),
        }
        tmp = APP_CONFIG_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(new_config, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(APP_CONFIG_PATH)
        logger.info("Конфигурация мигрирована")
        return True
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Ошибка миграции конфигурации: %s", e)
        return False


def _write_marker(success: bool, details: str = ""):
    MIGRATION_DIR.mkdir(parents=True, exist_ok=True)
    marker = {
        "date": datetime.now().isoformat(),
        "source": str(OLD_APPDATA),
        "target_data": str(DATA_DIR),
        "target_config": str(CONFIG_DIR),
        "result": "success" if success else "failed",
        "details": details,
        "source_version": "1.x",
        "target_version": "2.0.0",
    }
    MIGRATION_MARKER.write_text(json.dumps(marker, indent=2, ensure_ascii=False), encoding="utf-8")


def needs_migration() -> bool:
    if MIGRATION_MARKER.exists():
        return False
    if DB_PATH.exists():
        return False
    return OLD_APPDATA.exists() and _get_old_db_path() is not None


def migrate() -> bool:
    logger.info("Начало миграции из RusLOXPy")
    if MIGRATION_MARKER.exists():
        logger.info("Миграция уже выполнена")
        return True
    if DB_PATH.exists():
        logger.info("Новая БД уже существует, пропускаем миграцию")
        _write_marker(True, "skipped: new db already exists")
        return True

    old_db = _get_old_db_path()
    old_cfg = _get_old_config_path()

    if not old_db:
        logger.info("Старая БД не найдена")
        _write_marker(False, "old db not found")
        return False

    _checkpoint_old_db(old_db)

    db_ok = _copy_db(old_db)
    cfg_ok = True
    if old_cfg:
        cfg_ok = _migrate_config(old_cfg)

    success = db_ok and cfg_ok
    _write_marker(success, "db_ok={}, cfg_ok={}".format(db_ok, cfg_ok))

    if success:
        logger.info("Миграция завершена успешно")
    else:
        logger.error("Миграция завершена с ошибками")
    return success
