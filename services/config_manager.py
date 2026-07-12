import json
import logging
from pathlib import Path
from typing import Any

from config import CONFIG_PATH

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, path: Path = None):
        self._path = path or CONFIG_PATH
        self._data: dict = {}
        self._migrate_old()
        self._load()

    def _migrate_old(self):
        from config import APP_DIR
        old = APP_DIR / "config.json"
        if old.exists() and not self._path.exists():
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                self._path.write_text(old.read_text(encoding="utf-8"), encoding="utf-8")
                old.unlink()
            except OSError:
                logger.warning("Migration failed", exc_info=True)

    def _load(self):
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logger.warning("Config load failed", exc_info=True)
                self._data = {}
        else:
            self._data = {}

    def _save(self):
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value
        self._save()

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self.get(key, default))
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        try:
            return float(self.get(key, default))
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self.get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("1", "true", "yes")
        return bool(val)
