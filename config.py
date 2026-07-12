from pathlib import Path
import os

APP_NAME = "RusLOXPy"
APP_DIR = Path(__file__).parent
DATA_DIR = Path(os.getenv("APPDATA", APP_DIR)) / APP_NAME
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "tracker.db"
CONFIG_PATH = DATA_DIR / "config.json"

DEFAULT_POLL_INTERVAL = 1.5
DEFAULT_IDLE_THRESHOLD = 300
DEFAULT_SAVE_TITLES = True
DEFAULT_MINIMIZE_TO_TRAY = True

ICON_PATH = APP_DIR / "assets" / "images" / "icons" / "real-time.png"
