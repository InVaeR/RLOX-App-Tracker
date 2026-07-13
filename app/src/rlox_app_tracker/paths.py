import os
import sys
from pathlib import Path

from rlox_app_tracker.metadata import LAUNCHER_EXE_NAME, PRODUCT_NAME

_local_app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
_data_root = _local_app_data / PRODUCT_NAME

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent.parent.parent

ASSETS_DIR = APP_DIR / "assets"
ICON_PATH = ASSETS_DIR / "app.ico"
if not ICON_PATH.exists():
    ICON_PATH = ASSETS_DIR / "images" / "icons" / "real-time.png"

DATA_DIR = _data_root / "data"
CONFIG_DIR = _data_root / "config"
LOGS_DIR = _data_root / "logs"
UPDATES_DIR = _data_root / "updates"
MIGRATION_DIR = _data_root / "migration"
STATE_DIR = _data_root.parent / "Programs" / PRODUCT_NAME / "state"
INSTALL_DIR = STATE_DIR.parent

DB_PATH = DATA_DIR / "tracker.db"
APP_CONFIG_PATH = CONFIG_DIR / "app.json"
LAUNCHER_CONFIG_PATH = CONFIG_DIR / "launcher.json"
LOG_PATH = LOGS_DIR / "app.log"
LAUNCHER_LOG_PATH = LOGS_DIR / "launcher.log"
INSTALL_JSON_PATH = STATE_DIR / "install.json"
LAUNCHER_PATH = INSTALL_DIR / LAUNCHER_EXE_NAME

for d in [DATA_DIR, CONFIG_DIR, LOGS_DIR, UPDATES_DIR, MIGRATION_DIR, STATE_DIR]:
    d.mkdir(parents=True, exist_ok=True)
