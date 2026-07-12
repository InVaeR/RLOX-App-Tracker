При удалении всех данных в приложениях не обновляется список.
Если приложение не в списке оно не должно отображаться в активном окне.

# Directory Structure
```
assets/
  images/
    icons/
      apps.png
      point.png
      real-time.png
      setting.png
      stats.png
core/
  __init__.py
  idle_detector.py
  process_scanner.py
  tracker.py
  window_monitor.py
data/
  __init__.py
  database.py
  models.py
  repository.py
services/
  __init__.py
  autostart.py
  config_manager.py
  reporter.py
  watchlist.py
ui/
  components/
    __init__.py
    app_icons.py
    app_item_delegate.py
    bar_chart.py
    empty_state.py
    fade_stack.py
    legend.py
    pause_banner.py
    stat_card.py
  __init__.py
  dashboard_view.py
  main_window.py
  settings_view.py
  style.py
  theme.py
  watchlist_view.py
.gitignore
config.py
main.py
README.md
requirements.txt
```

# Files

## File: core/__init__.py
````python

````

## File: core/idle_detector.py
````python
from ctypes import Structure, windll, c_uint, sizeof, byref


class LASTINPUTINFO(Structure):
    _fields_ = [("cbSize", c_uint), ("dwTime", c_uint)]


def get_idle_seconds() -> float:
    info = LASTINPUTINFO()
    info.cbSize = sizeof(info)
    if not windll.user32.GetLastInputInfo(byref(info)):
        return 0.0
    millis = windll.kernel32.GetTickCount() - info.dwTime
    return millis / 1000.0
````

## File: core/process_scanner.py
````python
from typing import Dict, Set

import psutil


def get_running_process_names() -> Set[str]:
    names: Set[str] = set()
    for p in psutil.process_iter(["name"]):
        try:
            if p.info["name"]:
                names.add(p.info["name"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return names


def list_running_apps() -> Dict[str, str]:
    apps = {}
    for p in psutil.process_iter(["name", "exe"]):
        try:
            name = p.info["name"]
            exe = p.info["exe"]
            if name and exe:
                apps[name] = exe
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return apps
````

## File: core/tracker.py
````python
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal

from config import DEFAULT_POLL_INTERVAL, DEFAULT_IDLE_THRESHOLD
from core.window_monitor import get_active_window_process
from core.idle_detector import get_idle_seconds
from core.process_scanner import get_running_process_names
from data.repository import Repository
from data.models import Session, WatchedApp
from services.config_manager import ConfigManager


@dataclass
class _SessionState:
    session_id: int
    start_time: datetime
    title: str
    active_sec: int = 0
    background_sec: int = 0
    _acc: float = 0.0


class TrackerService(QObject):
    tracking_paused = Signal()
    tracking_resumed = Signal()
    stats_updated = Signal()
    active_app_info = Signal(dict)

    def __init__(self, repo: Repository, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.config = config
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._running = False
        self._paused = False
        self._sessions: Dict[int, _SessionState] = {}
        self._poll_interval = DEFAULT_POLL_INTERVAL
        self._idle_threshold = DEFAULT_IDLE_THRESHOLD
        self._save_titles = True
        self._last_tick_time: Optional[datetime] = None
        self._tick_count = 0
        self._watched_cache: List[WatchedApp] = []
        self._cache_dirty = True
        self._load_settings()

    def _load_settings(self):
        self._poll_interval = self.config.get_float("poll_interval", DEFAULT_POLL_INTERVAL)
        self._idle_threshold = self.config.get_int("idle_threshold", DEFAULT_IDLE_THRESHOLD)
        self._save_titles = self.config.get_bool("save_window_titles", True)

    def start(self):
        self._running = True
        self._paused = False
        self._last_tick_time = datetime.now()
        self._timer.start(int(self._poll_interval * 1000))

    def stop(self):
        self._running = False
        self._close_all_sessions()
        self._timer.stop()

    def pause(self):
        self._paused = True
        self._close_all_sessions()
        self.tracking_paused.emit()

    def resume(self):
        self._paused = False
        self.tracking_resumed.emit()

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_running(self) -> bool:
        return self._running

    def update_settings(self):
        self._load_settings()
        if self._running:
            self._timer.setInterval(int(self._poll_interval * 1000))

    def invalidate_cache(self):
        self._cache_dirty = True

    def _get_watched_apps(self) -> List[WatchedApp]:
        if self._cache_dirty or not self._watched_cache:
            self._watched_cache = self.repo.get_all_watched_apps()
            self._cache_dirty = False
        return self._watched_cache

    def _detect_sleep(self) -> bool:
        now = datetime.now()
        if self._last_tick_time is None:
            self._last_tick_time = now
            return False
        elapsed = (now - self._last_tick_time).total_seconds()
        self._last_tick_time = now
        max_gap = max(self._poll_interval * 3, 10)
        return elapsed > max_gap

    def _tick(self):
        if self._paused:
            return

        self._tick_count += 1
        now = datetime.now()

        slept = self._detect_sleep()
        if slept:
            self._close_all_sessions()

        idle_now = get_idle_seconds()
        window = get_active_window_process()
        focused_name = window["name"] if window else None
        running_names = get_running_process_names()
        watched_apps = self._get_watched_apps()
        watched_ids = {a.id: a for a in watched_apps if a.id}

        if slept:
            delta = 0
        elif self._last_tick_time:
            elapsed = (now - self._last_tick_time).total_seconds()
            delta = min(elapsed, self._poll_interval * 2)
        else:
            delta = self._poll_interval

        for app in watched_apps:
            if app.id is None:
                continue
            is_running = app.process_name in running_names
            is_focused = focused_name == app.process_name
            state = self._sessions.get(app.id)

            if not is_running:
                if state:
                    self._close_session(app.id, state)
                continue

            if not state:
                title = window["title"] if is_focused and self._save_titles else ""
                sess = Session(app_id=app.id, start_time=now, window_title=title)
                sid = self.repo.add_session(sess)
                self._sessions[app.id] = _SessionState(session_id=sid, start_time=now, title=title)

            state = self._sessions[app.id]
            delta_int = int(delta)
            state._acc += delta - delta_int
            if state._acc >= 1.0:
                extra = int(state._acc)
                delta_int += extra
                state._acc -= extra

            if delta_int > 0:
                if is_focused and idle_now <= self._idle_threshold:
                    state.active_sec += delta_int
                    if self._save_titles and window:
                        state.title = window["title"]
                else:
                    state.background_sec += delta_int

        for app_id, state in list(self._sessions.items()):
            if app_id not in watched_ids:
                self._close_session(app_id, state)

        watched_running = [
            {"name": a.process_name, "display_name": a.display_name or a.process_name}
            for a in watched_apps if a.process_name in running_names
        ]
        focused_app_id = None
        focused_sec = 0
        focused_display = ""
        for app in watched_apps:
            if app.id and app.process_name == focused_name:
                focused_app_id = app.id
                focused_display = app.display_name or app.process_name
                break
        if focused_app_id and focused_app_id in self._sessions:
            state = self._sessions[focused_app_id]
            focused_sec = state.active_sec
        self.active_app_info.emit({
            "paused": self._paused,
            "running_apps": watched_running,
            "focused": focused_name,
            "focused_display": focused_display,
            "focused_sec": focused_sec,
        })

        self._periodic_flush()

    def _close_session(self, app_id: int, state: _SessionState):
        now = datetime.now()
        elapsed = int((now - state.start_time).total_seconds())
        active = min(state.active_sec, elapsed)
        background = min(state.background_sec, elapsed - active)
        sess = Session(
            id=state.session_id,
            end_time=now,
            duration_sec=active + background,
            active_sec=active,
            background_sec=background,
            window_title=state.title if state.title else None,
        )
        self.repo.update_session(sess)
        del self._sessions[app_id]
        self.stats_updated.emit()

    def _close_all_sessions(self):
        for app_id, state in list(self._sessions.items()):
            self._close_session(app_id, state)

    def _periodic_flush(self):
        if self._tick_count % 10 != 0:
            return
        for app_id, state in self._sessions.items():
            now = datetime.now()
            elapsed = int((now - state.start_time).total_seconds())
            active = min(state.active_sec, elapsed)
            background = min(state.background_sec, elapsed - active)
            self.repo.flush_session(
                state.session_id,
                active + background,
                active,
                background,
                state.title,
            )
````

## File: core/window_monitor.py
````python
from typing import Optional, Dict

import win32gui
import win32process
import psutil


def get_active_window_process() -> Optional[Dict]:
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        return {
            "pid": pid,
            "name": proc.name(),
            "exe": proc.exe(),
            "title": win32gui.GetWindowText(hwnd),
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None
````

## File: data/__init__.py
````python

````

## File: data/database.py
````python
import sqlite3
import threading
from pathlib import Path

from config import DB_PATH


class Database:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DB_PATH
        self.lock = threading.Lock()
        self.conn: sqlite3.Connection = None
        self._connect()
        self._migrate()

    def _connect(self):
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")

    def _migrate(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS watched_apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_name TEXT UNIQUE NOT NULL,
                display_name TEXT,
                exe_path TEXT,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL,
                window_title TEXT,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                duration_sec INTEGER,
                idle_sec INTEGER DEFAULT 0,
                FOREIGN KEY (app_id) REFERENCES watched_apps(id)
            );

        """)
        self._migrate_sessions()
        self.conn.commit()

    def _migrate_sessions(self):
        cur = self.conn.cursor()
        existing = [r["name"] for r in cur.execute("PRAGMA table_info(sessions)").fetchall()]
        for col in ("active_sec", "background_sec"):
            if col not in existing:
                cur.execute(f"ALTER TABLE sessions ADD COLUMN {col} INTEGER DEFAULT 0")

    def execute(self, sql: str, params=()):
        with self.lock:
            return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_seq):
        with self.lock:
            return self.conn.executemany(sql, params_seq)

    def commit(self):
        with self.lock:
            self.conn.commit()

    def close(self):
        self.conn.close()
````

## File: data/models.py
````python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WatchedApp:
    id: Optional[int] = None
    process_name: str = ""
    display_name: Optional[str] = None
    exe_path: Optional[str] = None
    added_at: Optional[datetime] = None


@dataclass
class Session:
    id: Optional[int] = None
    app_id: int = 0
    window_title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_sec: Optional[int] = None
    active_sec: Optional[int] = 0
    background_sec: Optional[int] = 0
    idle_sec: Optional[int] = 0


@dataclass
class AppStats:
    process_name: str
    display_name: str
    total_seconds: int
    active_seconds: int
    background_seconds: int
    session_count: int
````

## File: data/repository.py
````python
from datetime import datetime
from typing import List, Optional

from data.database import Database
from data.models import WatchedApp, Session, AppStats


class Repository:
    def __init__(self, db: Database):
        self.db = db

    def add_watched_app(self, app: WatchedApp) -> int:
        existing = self.db.execute(
            "SELECT id FROM watched_apps WHERE process_name = ?", (app.process_name,)
        ).fetchone()
        if existing:
            return -1
        cur = self.db.execute(
            "INSERT INTO watched_apps (process_name, display_name, exe_path) VALUES (?, ?, ?)",
            (app.process_name, app.display_name, app.exe_path),
        )
        self.db.commit()
        return cur.lastrowid or 0

    def remove_watched_app(self, app_id: int):
        self.db.execute("DELETE FROM sessions WHERE app_id = ?", (app_id,))
        self.db.execute("DELETE FROM watched_apps WHERE id = ?", (app_id,))
        self.db.commit()

    def get_all_watched_apps(self) -> List[WatchedApp]:
        rows = self.db.execute("SELECT * FROM watched_apps ORDER BY added_at").fetchall()
        return [WatchedApp(**dict(r)) for r in rows]

    def get_watched_app_by_name(self, name: str) -> Optional[WatchedApp]:
        row = self.db.execute(
            "SELECT * FROM watched_apps WHERE process_name = ?", (name,)
        ).fetchone()
        return WatchedApp(**dict(row)) if row else None

    def is_watched(self, process_name: str) -> bool:
        row = self.db.execute(
            "SELECT 1 FROM watched_apps WHERE process_name = ?", (process_name,)
        ).fetchone()
        return row is not None

    def add_session(self, session: Session) -> int:
        cur = self.db.execute(
            "INSERT INTO sessions (app_id, window_title, start_time, end_time, duration_sec, active_sec, background_sec) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session.app_id, session.window_title, session.start_time, session.end_time, session.duration_sec, session.active_sec, session.background_sec),
        )
        self.db.commit()
        return cur.lastrowid or 0

    def update_session(self, session: Session):
        self.db.execute(
            "UPDATE sessions SET end_time = ?, duration_sec = ?, active_sec = ?, background_sec = ?, window_title = COALESCE(?, window_title) WHERE id = ?",
            (session.end_time, session.duration_sec, session.active_sec, session.background_sec, session.window_title, session.id),
        )
        self.db.commit()

    def flush_session(self, session_id: int, duration_sec: int, active_sec: int, background_sec: int, title: str = None):
        if title:
            self.db.execute(
                "UPDATE sessions SET duration_sec = ?, active_sec = ?, background_sec = ?, window_title = ? WHERE id = ?",
                (duration_sec, active_sec, background_sec, title, session_id),
            )
        else:
            self.db.execute(
                "UPDATE sessions SET duration_sec = ?, active_sec = ?, background_sec = ? WHERE id = ?",
                (duration_sec, active_sec, background_sec, session_id),
            )
        self.db.commit()

    def get_open_session(self, app_id: int) -> Optional[Session]:
        row = self.db.execute(
            "SELECT * FROM sessions WHERE app_id = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1",
            (app_id,),
        ).fetchone()
        return Session(**dict(row)) if row else None

    def get_all_open_sessions(self) -> List[Session]:
        rows = self.db.execute(
            "SELECT * FROM sessions WHERE end_time IS NULL ORDER BY start_time"
        ).fetchall()
        return [Session(**dict(r)) for r in rows]

    def close_all_active_sessions(self):
        self.db.execute(
            "UPDATE sessions SET end_time = ?, duration_sec = COALESCE(active_sec,0) + COALESCE(background_sec,0) WHERE end_time IS NULL",
            (datetime.now(),),
        )
        self.db.commit()

    def get_stats(self, period_days: int = 1) -> List[AppStats]:
        if period_days is None:
            query = """
                SELECT w.process_name, w.display_name,
                       COALESCE(SUM(s.duration_sec), 0) as total_seconds,
                       COALESCE(SUM(s.active_sec), 0) as active_seconds,
                       COALESCE(SUM(s.background_sec), 0) as background_seconds,
                       COUNT(s.id) as session_count
                FROM watched_apps w
                LEFT JOIN sessions s ON s.app_id = w.id
                    AND s.duration_sec IS NOT NULL
                GROUP BY w.id
                ORDER BY total_seconds DESC
            """
            rows = self.db.execute(query).fetchall()
        elif period_days == 1:
            query = """
                SELECT w.process_name, w.display_name,
                       COALESCE(SUM(s.duration_sec), 0) as total_seconds,
                       COALESCE(SUM(s.active_sec), 0) as active_seconds,
                       COALESCE(SUM(s.background_sec), 0) as background_seconds,
                       COUNT(s.id) as session_count
                FROM watched_apps w
                LEFT JOIN sessions s ON s.app_id = w.id
                    AND s.start_time >= datetime('now', 'localtime', 'start of day')
                    AND s.duration_sec IS NOT NULL
                GROUP BY w.id
                ORDER BY total_seconds DESC
            """
            rows = self.db.execute(query).fetchall()
        else:
            days_offset = period_days - 1
            query = """
                SELECT w.process_name, w.display_name,
                       COALESCE(SUM(s.duration_sec), 0) as total_seconds,
                       COALESCE(SUM(s.active_sec), 0) as active_seconds,
                       COALESCE(SUM(s.background_sec), 0) as background_seconds,
                       COUNT(s.id) as session_count
                FROM watched_apps w
                LEFT JOIN sessions s ON s.app_id = w.id
                    AND s.start_time >= datetime('now', 'localtime', 'start of day', ?)
                    AND s.duration_sec IS NOT NULL
                GROUP BY w.id
                ORDER BY total_seconds DESC
            """
            rows = self.db.execute(query, (f"-{days_offset} days",)).fetchall()
        return [AppStats(**dict(r)) for r in rows]

    def get_today_seconds_by_app(self) -> dict:
        rows = self.db.execute("""
            SELECT w.process_name, w.display_name,
                   COALESCE(SUM(s.active_sec), 0) + COALESCE(SUM(s.background_sec), 0) as total_seconds
            FROM watched_apps w
            LEFT JOIN sessions s ON s.app_id = w.id
                AND s.start_time >= datetime('now', 'localtime', 'start of day')
                AND s.duration_sec IS NOT NULL
            GROUP BY w.id
        """).fetchall()
        return {r["process_name"]: r["total_seconds"] for r in rows}

    def update_display_name(self, app_id: int, name: str):
        self.db.execute(
            "UPDATE watched_apps SET display_name = ? WHERE id = ?", (name, app_id)
        )
        self.db.commit()

    def clear_all_data(self):
        self.db.execute("DELETE FROM sessions")
        self.db.execute("DELETE FROM watched_apps")
        self.db.commit()
````

## File: services/__init__.py
````python

````

## File: services/autostart.py
````python
import sys
import winreg

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def enable_autostart(app_name: str = "RusLOXPy"):
    path = sys.executable
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, app_name, 0, winreg.REG_SZ, f'"{path}"')


def disable_autostart(app_name: str = "RusLOXPy"):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as k:
        try:
            winreg.DeleteValue(k, app_name)
        except FileNotFoundError:
            pass


def is_autostart_enabled(app_name: str = "RusLOXPy") -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, app_name)
            return True
    except FileNotFoundError:
        return False
````

## File: services/config_manager.py
````python
import json
from pathlib import Path
from typing import Any

from config import CONFIG_PATH


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
                pass

    def _load(self):
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
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
````

## File: services/reporter.py
````python
from typing import List

from data.repository import Repository
from data.models import AppStats


class Reporter:
    def __init__(self, repo: Repository):
        self.repo = repo

    def get_daily_stats(self) -> List[AppStats]:
        return self.repo.get_stats(period_days=1)

    def get_weekly_stats(self) -> List[AppStats]:
        return self.repo.get_stats(period_days=7)

    def get_monthly_stats(self) -> List[AppStats]:
        return self.repo.get_stats(period_days=30)

    def get_all_time_stats(self) -> List[AppStats]:
        return self.repo.get_stats(period_days=None)
````

## File: services/watchlist.py
````python
from typing import List, Optional

from data.repository import Repository
from data.models import WatchedApp


class WatchListManager:
    def __init__(self, repo: Repository):
        self.repo = repo

    def add_app(self, process_name: str, exe_path: str = None, display_name: str = None) -> int:
        app = WatchedApp(
            process_name=process_name,
            display_name=display_name or process_name,
            exe_path=exe_path,
        )
        return self.repo.add_watched_app(app)

    def remove_app(self, app_id: int):
        self.repo.remove_watched_app(app_id)

    def get_all(self) -> List[WatchedApp]:
        return self.repo.get_all_watched_apps()

    def is_watched(self, process_name: str) -> bool:
        return self.repo.is_watched(process_name)

    def get_by_name(self, name: str) -> Optional[WatchedApp]:
        return self.repo.get_watched_app_by_name(name)
````

## File: ui/components/__init__.py
````python

````

## File: ui/components/app_icons.py
````python
import os
from pathlib import Path
from PySide6.QtWidgets import QFileIconProvider
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QFileInfo
from config import APP_DIR

_provider = QFileIconProvider()
_cache: dict[str, QIcon] = {}

_ICONS_DIR = APP_DIR / "assets" / "images" / "icons"
_asset_cache: dict[str, QIcon] = {}


def get_app_icon(exe_path: str | None) -> QIcon | None:
    if not exe_path:
        return None
    if exe_path in _cache:
        return _cache[exe_path]
    if os.path.exists(exe_path):
        icon = _provider.icon(QFileInfo(exe_path))
        _cache[exe_path] = icon
        return icon
    return None


def asset_icon(name: str) -> QIcon:
    if name in _asset_cache:
        return _asset_cache[name]
    p = _ICONS_DIR / name
    if p.exists():
        icon = QIcon(str(p))
        _asset_cache[name] = icon
        return icon
    return QIcon()


def asset_pixmap(name: str, size: int = 48) -> QPixmap:
    icon = asset_icon(name)
    if not icon.isNull():
        return icon.pixmap(size, size)
    return QPixmap()
````

## File: ui/components/app_item_delegate.py
````python
from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt, QSize, QRect
from PySide6.QtGui import QColor, QFont
from ui.theme import PALETTE as C


class AppItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(0, 54)

    def paint(self, painter, option, index):
        painter.save()
        rect = option.rect

        if option.state & QStyle.StateFlag.State_Selected:
            painter.setBrush(QColor(C.accent_soft))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect.adjusted(4, 2, -4, -2), 8, 8)
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.setBrush(QColor(C.surface_hover))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect.adjusted(4, 2, -4, -2), 8, 8)

        icon = index.data(Qt.ItemDataRole.DecorationRole)
        icon_size = 28
        icon_x = rect.left() + 14
        icon_y = rect.top() + (rect.height() - icon_size) // 2
        if icon:
            icon.paint(painter, QRect(icon_x, icon_y, icon_size, icon_size))

        text_x = icon_x + icon_size + 12
        text_w = rect.right() - text_x - 12

        name = index.data(Qt.ItemDataRole.DisplayRole) or ""
        exe = index.data(Qt.ItemDataRole.UserRole) or ""

        painter.setPen(QColor(C.text))
        f = QFont(painter.font())
        f.setPointSize(10)
        f.setBold(True)
        painter.setFont(f)
        fm = painter.fontMetrics()
        name_el = fm.elidedText(name, Qt.TextElideMode.ElideRight, text_w)
        painter.drawText(text_x, rect.top() + 12, text_w, 18,
                         Qt.AlignmentFlag.AlignVCenter, name_el)

        painter.setPen(QColor(C.text_dim))
        f2 = QFont(painter.font())
        f2.setPointSize(8)
        f2.setBold(False)
        painter.setFont(f2)
        fm2 = painter.fontMetrics()
        exe_el = fm2.elidedText(exe, Qt.TextElideMode.ElideMiddle, text_w)
        painter.drawText(text_x, rect.top() + 30, text_w, 16,
                         Qt.AlignmentFlag.AlignVCenter, exe_el)

        painter.restore()
````

## File: ui/components/bar_chart.py
````python
from PySide6.QtWidgets import QWidget, QScrollArea
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QColor, QPalette
from ui.theme import PALETTE as C


class BarChartWidget(QWidget):
    _left = 110
    _right = 100
    _gap = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stats = []

    def set_stats(self, stats):
        self._stats = [s for s in stats if s.active_seconds + s.background_seconds > 0]
        self.update()

    def sizeHint(self):
        rows = max(1, len(self._stats))
        return QSize(400, rows * 34 + 16)

    def paintEvent(self, event):
        if not self._stats:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        count = len(self._stats)
        bar_h = max(24, min(36, (h - 16) // count))
        total = max(s.active_seconds + s.background_seconds for s in self._stats)
        if total == 0:
            return
        active_color = QColor(C.accent)
        bg_color = QColor(C.background_bar)
        text_color = QColor(C.text)
        radius = 4
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        fm = painter.fontMetrics()
        bar_area = max(0, w - self._left - self._right - self._gap * 2)

        for i, s in enumerate(self._stats):
            y = 8 + i * (bar_h + 6)
            name = s.display_name or s.process_name
            total_sec = s.active_seconds + s.background_seconds

            painter.setPen(text_color)
            elided = fm.elidedText(name, Qt.TextElideMode.ElideRight, self._left - 4)
            painter.drawText(4, y, self._left - 4, bar_h, Qt.AlignmentFlag.AlignVCenter, elided)

            a_w = int((s.active_seconds / total) * bar_area) if s.active_seconds else 0
            b_w = int((s.background_seconds / total) * bar_area) if s.background_seconds else 0
            bx = self._left + self._gap

            if a_w > 0:
                painter.setBrush(active_color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bx, y, a_w, bar_h, radius, radius)
            if b_w > 0:
                painter.setBrush(bg_color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bx + a_w, y, b_w, bar_h, radius, radius)

            from ui.theme import _fmt
            label = _fmt(total_sec)
            painter.setPen(text_color)
            painter.drawText(bx + a_w + b_w + self._gap, y, self._right - 4, bar_h,
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, label)

        painter.end()


class ChartContainer(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._chart = BarChartWidget(self)
        self.setWidgetResizable(True)
        self.setFrameShape(self.Shape.NoFrame)
        self.setWidget(self._chart)
        self.setMaximumHeight(280)

    def set_stats(self, stats):
        self._chart.set_stats(stats)
````

## File: ui/components/empty_state.py
````python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from ui.theme import PALETTE as C


class EmptyState(QWidget):
    def __init__(self, title: str, subtitle: str,
                 button_text: str = "", on_click=None,
                 pixmap: QPixmap = None, emoji: str = ""):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(12)

        ic = QLabel()
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if pixmap and not pixmap.isNull():
            ic.setPixmap(pixmap)
        elif emoji:
            ic.setText(emoji)
            ic.setStyleSheet("font-size:52px;")
        lay.addWidget(ic)

        t = QLabel(title)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(f"font-size:17px; font-weight:600; color:{C.text};")

        s = QLabel(subtitle)
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.setStyleSheet(f"font-size:13px; color:{C.text_muted};")

        lay.addWidget(t)
        lay.addWidget(s)

        if button_text and on_click:
            btn = QPushButton(button_text)
            btn.setObjectName("primary")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(on_click)
            lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
````

## File: ui/components/fade_stack.py
````python
from PySide6.QtWidgets import QStackedWidget, QGraphicsOpacityEffect
from PySide6.QtCore import QPropertyAnimation, QEasingCurve


class FadeStack(QStackedWidget):
    def setCurrentIndex(self, index):
        if index == self.currentIndex():
            return
        super().setCurrentIndex(index)
        w = self.currentWidget()
        eff = QGraphicsOpacityEffect(w)
        w.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(180)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: w.setGraphicsEffect(None))
        anim.start()
        self._anim = anim
````

## File: ui/components/legend.py
````python
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from ui.theme import PALETTE as C


class Legend(QWidget):
    def __init__(self):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.addWidget(self._dot(C.accent, "Активное"))
        lay.addWidget(self._dot(C.background_bar, "Фоновое"))
        lay.addStretch()

    def _dot(self, color, text):
        w = QLabel(
            f"<span style='color:{color}'>●</span> "
            f"<span style='color:{C.text_muted}'>{text}</span>"
        )
        w.setStyleSheet("font-size:12px;")
        return w
````

## File: ui/components/pause_banner.py
````python
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from ui.theme import PALETTE as C


class PauseBanner(QFrame):
    resume_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {C.warning};
                border-radius: 0;
            }}
            QLabel {{ color: #1a1200; font-weight: 600; font-size: 13px; }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.addWidget(QLabel("Отслеживание приостановлено"))
        lay.addStretch()
        btn = QPushButton("Возобновить")
        btn.setStyleSheet(
            "background:#1a1200; color:#fff; border:none; "
            "border-radius:6px; padding:6px 14px;"
        )
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.resume_clicked.emit)
        lay.addWidget(btn)
        self.hide()
````

## File: ui/components/stat_card.py
````python
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from ui.theme import PALETTE as C, SPACING as S


class StatCard(QFrame):
    def __init__(self, title: str, accent: str = C.accent):
        super().__init__()
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(S.lg, S.md, S.lg, S.md)
        lay.setSpacing(S.xs)

        self._title = QLabel(title)
        self._title.setStyleSheet(
            f"color:{C.text_muted}; font-size:12px; font-weight:600;"
        )

        self._value = QLabel("—")
        self._value.setStyleSheet(f"color:{accent}; font-size:28px; font-weight:700;")

        self._sub = QLabel("")
        self._sub.setStyleSheet(f"color:{C.text_dim}; font-size:12px;")

        lay.addWidget(self._title)
        lay.addWidget(self._value)
        lay.addWidget(self._sub)

    def set_value(self, value: str, sub: str = ""):
        self._value.setText(value)
        self._sub.setText(sub)
````

## File: ui/__init__.py
````python

````

## File: ui/dashboard_view.py
````python
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QComboBox,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QGraphicsOpacityEffect, QStackedWidget,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPalette, QPainter, QPixmap

from services.reporter import Reporter
from ui.theme import _fmt, PALETTE as C, SPACING as S
from ui.components.stat_card import StatCard
from ui.components.bar_chart import ChartContainer
from ui.components.legend import Legend
from ui.components.empty_state import EmptyState
from ui.components.app_icons import asset_pixmap
from data.models import AppStats


class NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        return (self.data(Qt.ItemDataRole.UserRole) or 0) < \
               (other.data(Qt.ItemDataRole.UserRole) or 0)


class LiveCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        ll = QHBoxLayout(self)
        ll.setContentsMargins(16, 14, 16, 14)

        pulse_pix = asset_pixmap("point.png", 16)
        self._pulse = QLabel()
        if not pulse_pix.isNull():
            pm = QPixmap(pulse_pix)
            from PySide6.QtGui import QPainter as QP, QColor as QC
            p = QP(pm)
            p.setCompositionMode(QP.CompositionMode.CompositionMode_SourceIn)
            p.fillRect(pm.rect(), QC(C.success))
            p.end()
            self._pulse.setPixmap(pm)
        else:
            self._pulse.setText("●")
            self._pulse.setStyleSheet(f"color:{C.success}; font-size:14px;")
        eff = QGraphicsOpacityEffect(self._pulse)
        self._pulse.setGraphicsEffect(eff)
        self._anim = QPropertyAnimation(eff, b"opacity")
        self._anim.setDuration(1200)
        self._anim.setStartValue(1.0)
        self._anim.setKeyValueAt(0.5, 0.3)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.start()

        texts = QVBoxLayout()
        texts.setSpacing(2)
        self._live_name = QLabel("Ожидание…")
        self._live_name.setStyleSheet(
            f"font-size:15px; font-weight:600; color:{C.text};")
        self._live_detail = QLabel("Нет активного приложения")
        self._live_detail.setStyleSheet(
            f"font-size:12px; color:{C.text_muted};")
        texts.addWidget(self._live_name)
        texts.addWidget(self._live_detail)

        self._live_timer = QLabel("00:00")
        self._live_timer.setStyleSheet(
            f"font-size:20px; font-weight:700; color:{C.accent};")

        ll.addWidget(self._pulse)
        ll.addLayout(texts, 1)
        ll.addWidget(self._live_timer)

    def _tint_pulse(self, color: str):
        pulse_pix = asset_pixmap("point.png", 16)
        if not pulse_pix.isNull():
            pm = QPixmap(pulse_pix)
            from PySide6.QtGui import QPainter as QP, QColor as QC
            p = QP(pm)
            p.setCompositionMode(QP.CompositionMode.CompositionMode_SourceIn)
            p.fillRect(pm.rect(), QC(color))
            p.end()
            self._pulse.setPixmap(pm)
        else:
            self._pulse.setStyleSheet(f"color:{color}; font-size:14px;")

    def update_info(self, info: dict):
        if not info or info.get("paused"):
            self._live_name.setText("Трекинг приостановлен")
            self._live_detail.setText("Нажмите «Возобновить» в меню трея")
            self._live_timer.setText("—")
            self._tint_pulse(C.warning)
            return
        focused = info.get("focused", "")
        display_name = info.get("focused_display", "") or focused
        sec = info.get("focused_sec", 0)
        if focused:
            self._live_name.setText(display_name)
            self._live_detail.setText("Активное окно")
            self._live_timer.setText(_fmt(sec))
            self._tint_pulse(C.success)
        else:
            running = info.get("running_apps", [])
            if running:
                names = ", ".join(
                    a.get("display_name", a["name"]) for a in running[:5])
                self._live_name.setText(f"Запущено: {len(running)}")
                self._live_detail.setText(names)
            else:
                self._live_name.setText("Ожидание…")
                self._live_detail.setText("Нет запущенных отслеживаемых приложений")
            self._live_timer.setText("—")
            self._tint_pulse(C.text_dim)


class DashboardView(QWidget):
    def __init__(self, reporter: Reporter, on_add_app=None, parent=None):
        super().__init__(parent)
        self.reporter = reporter
        self._on_add_app = on_add_app
        self._stats: list[AppStats] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(S.xl, S.xl, S.xl, S.xl)
        root.setSpacing(S.lg)

        self.live_card = LiveCard()
        root.addWidget(self.live_card)

        cards_row = QGridLayout()
        cards_row.setSpacing(S.md)
        self.card_total = StatCard("Всего сегодня", C.accent)
        self.card_active = StatCard("Активное время", C.success)
        self.card_running = StatCard("Запущено сейчас", C.warning)
        self.card_top = StatCard("Топ приложение", C.text)
        for i, card in enumerate(
            [self.card_total, self.card_active, self.card_running, self.card_top]
        ):
            cards_row.addWidget(card, 0, i)
        root.addLayout(cards_row)

        period_row = QHBoxLayout()
        period_row.setContentsMargins(0, 0, 0, 0)
        period_label = QLabel("Период:")
        period_label.setStyleSheet(
            f"color:{C.text_muted}; font-size:12px; font-weight:600;")
        period_row.addWidget(period_label)
        self.period_combo = QComboBox()
        self.period_combo.addItems(
            ["Сегодня", "Неделя", "Месяц", "За всё время"])
        self.period_combo.currentIndexChanged.connect(self._on_period_change)
        period_row.addWidget(self.period_combo)
        period_row.addStretch()
        root.addLayout(period_row)

        self._chart_container = ChartContainer()
        root.addWidget(self._chart_container)

        self._legend = Legend()
        root.addWidget(self._legend)

        self._content_stack = QStackedWidget()
        self._empty = EmptyState(
            "Нет данных",
            "Запустите отслеживаемое приложение, чтобы увидеть статистику",
            pixmap=asset_pixmap("stats.png", 64),
        )
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["Приложение", "Активное", "Фоновое", "Сессий"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setDefaultSectionSize(32)
        self._table.setSortingEnabled(True)
        self._content_stack.addWidget(self._table)
        self._content_stack.addWidget(self._empty)
        root.addWidget(self._content_stack, 1)

        self.refresh()

    def update_live(self, info: dict):
        self.live_card.update_info(info)

    def refresh(self):
        idx = self.period_combo.currentIndex()
        if idx == 0:
            stats = self.reporter.get_daily_stats()
        elif idx == 1:
            stats = self.reporter.get_weekly_stats()
        elif idx == 2:
            stats = self.reporter.get_monthly_stats()
        else:
            stats = self.reporter.get_all_time_stats()
        self._stats = stats
        self._update_contents(stats)

    def _on_period_change(self):
        self.refresh()

    def refresh_live_only(self):
        self._update_cards(self._stats)

    def _update_contents(self, stats):
        self._chart_container.set_stats(stats)
        self._update_cards(stats)
        self._update_table(stats)

    def _update_cards(self, stats):
        total = sum(s.active_seconds + s.background_seconds for s in stats)
        active = sum(s.active_seconds for s in stats)
        self.card_total.set_value(_fmt(total))
        self.card_active.set_value(
            _fmt(active),
            f"{int(active / total * 100) if total else 0}% от общего",
        )
        running = len([s for s in stats if s.active_seconds + s.background_seconds > 0])
        self.card_running.set_value(str(running))
        top = max(
            stats,
            key=lambda s: s.active_seconds + s.background_seconds,
            default=None,
        )
        if top and (top.active_seconds + top.background_seconds) > 0:
            self.card_top.set_value(
                top.display_name or top.process_name,
                _fmt(top.active_seconds + top.background_seconds),
            )

    def _update_table(self, stats):
        if not stats:
            self._content_stack.setCurrentWidget(self._empty)
            return
        self._content_stack.setCurrentWidget(self._table)

        sorting = self._table.isSortingEnabled()
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(stats))
        for i, s in enumerate(stats):
            name = s.display_name or s.process_name
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.ItemDataRole.UserRole, name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 0, name_item)

            for col, val, raw in [
                (1, _fmt(s.active_seconds), s.active_seconds),
                (2, _fmt(s.background_seconds), s.background_seconds),
                (3, str(s.session_count), s.session_count),
            ]:
                item = NumericItem(val)
                item.setData(Qt.ItemDataRole.UserRole, raw)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(i, col, item)
        self._table.setSortingEnabled(sorting)
````

## File: ui/main_window.py
````python
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QButtonGroup, QStatusBar, QSystemTrayIcon, QMenu,
    QApplication,
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor, QAction

from ui.dashboard_view import DashboardView
from ui.watchlist_view import WatchListView
from ui.settings_view import SettingsView
from ui.components.fade_stack import FadeStack
from ui.components.pause_banner import PauseBanner
from ui.components.app_icons import asset_icon, asset_pixmap
from ui.theme import PALETTE as C, SPACING as S
from core.tracker import TrackerService
from data.repository import Repository
from services.config_manager import ConfigManager
from services.reporter import Reporter
from services.watchlist import WatchListManager
from config import ICON_PATH


class NavButton(QPushButton):
    def __init__(self, text, icon_name=""):
        super().__init__(f"  {text}")
        self.setObjectName("navItem")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_name:
            ico = asset_icon(icon_name)
            if not ico.isNull():
                self.setIcon(ico)
                self.setIconSize(QSize(20, 20))


class MainWindow(QMainWindow):
    def __init__(self, repo: Repository, tracker: TrackerService,
                 config: ConfigManager):
        super().__init__()
        self.repo = repo
        self.tracker = tracker
        self.config = config
        self._closing = False

        self.setWindowTitle("RusLOXPy")
        self.setMinimumSize(960, 640)

        watchlist_mgr = WatchListManager(repo)
        reporter = Reporter(repo)

        self.dashboard_view = DashboardView(reporter, on_add_app=self._show_apps)
        self.watchlist_view = WatchListView(watchlist_mgr, repo,
                                            on_changed=self.tracker.invalidate_cache)
        self.settings_view = SettingsView(config, repo, on_settings_changed=self._on_settings_changed)

        root = QWidget()
        root.setObjectName("root")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(S.md, S.xl, S.md, S.lg)
        sb.setSpacing(S.xs)

        logo_pix = asset_pixmap("real-time.png", 24)
        logo = QLabel()
        if not logo_pix.isNull():
            logo.setPixmap(logo_pix)
        logo.setText("  RusLOXPy")
        logo.setStyleSheet(
            "font-size:18px; font-weight:700; padding:8px 14px 20px 14px;")
        sb.addWidget(logo)

        self.nav_group = QButtonGroup(self)
        self.btn_dash = NavButton("Дашборд", "stats.png")
        self.btn_apps = NavButton("Приложения", "apps.png")
        self.btn_settings = NavButton("Настройки", "setting.png")
        for i, b in enumerate(
            [self.btn_dash, self.btn_apps, self.btn_settings]
        ):
            self.nav_group.addButton(b, i)
            sb.addWidget(b)
        sb.addStretch()

        self.status_dot = QLabel("● Отслеживание активно")
        self.status_dot.setStyleSheet(
            f"color:{C.success}; font-size:12px; padding:8px 14px;")
        sb.addWidget(self.status_dot)

        self.stack = FadeStack()
        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.watchlist_view)
        self.stack.addWidget(self.settings_view)

        self.pause_banner = PauseBanner()
        content_col = QVBoxLayout()
        content_col.setContentsMargins(0, 0, 0, 0)
        content_col.setSpacing(0)
        content_col.addWidget(self.pause_banner)
        content_col.addWidget(self.stack, 1)

        layout.addWidget(sidebar)
        layout.addLayout(content_col, 1)
        self.setCentralWidget(root)

        self.nav_group.idClicked.connect(self._on_nav)
        self.btn_dash.setChecked(True)

        self.setStatusBar(QStatusBar())
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status)
        self._status_timer.start(1000)

        self._live_refresh = QTimer(self)
        self._live_refresh.timeout.connect(self._on_live_refresh)
        self._live_refresh.start(5000)

        self._setup_tray()

        self.tracker.stats_updated.connect(self.dashboard_view.refresh)
        self.tracker.active_app_info.connect(self.dashboard_view.update_live)
        self.tracker.tracking_paused.connect(self._on_tracking_paused)
        self.tracker.tracking_resumed.connect(self._on_tracking_resumed)
        self.pause_banner.resume_clicked.connect(self.tracker.resume)

    def _on_nav(self, idx: int):
        self.stack.setCurrentIndex(idx)

    def _show_apps(self):
        self.btn_apps.setChecked(True)
        self.stack.setCurrentIndex(1)

    def _on_settings_changed(self):
        self.tracker.update_settings()

    def _on_tracking_paused(self):
        self._pause_action.setChecked(True)
        self.status_dot.setText("● Пауза")
        self.status_dot.setStyleSheet(
            f"color:{C.warning}; font-size:12px; padding:8px 14px;")
        self.pause_banner.show()

    def _on_tracking_resumed(self):
        self._pause_action.setChecked(False)
        self.status_dot.setText("● Отслеживание активно")
        self.status_dot.setStyleSheet(
            f"color:{C.success}; font-size:12px; padding:8px 14px;")
        self.pause_banner.hide()

    def _refresh_status(self):
        if self.tracker.is_paused:
            self.statusBar().showMessage("Отслеживание приостановлено")
        else:
            n = len(self.repo.get_all_watched_apps())
            self.statusBar().showMessage(
                f"Отслеживается приложений: {n}  ·  "
                f"обновлено {datetime.now():%H:%M:%S}")

    def _on_live_refresh(self):
        if self.stack.currentWidget() is self.dashboard_view:
            self.dashboard_view.refresh()
        elif self.stack.currentWidget() is self.watchlist_view:
            self.watchlist_view.refresh_times()

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("RusLOXPy")
        icon = self._load_icon()
        self.tray_icon.setIcon(icon)
        self.setWindowIcon(icon)
        tray_menu = QMenu(self)
        show_action = QAction("Показать", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)
        self._pause_action = QAction("Пауза", self)
        self._pause_action.setCheckable(True)
        self._pause_action.triggered.connect(self._toggle_pause)
        tray_menu.addAction(self._pause_action)
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self._quit)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def _toggle_pause(self, checked):
        if checked:
            self.tracker.pause()
        else:
            self.tracker.resume()

    def _load_icon(self) -> QIcon:
        if ICON_PATH.exists():
            return QIcon(str(ICON_PATH))
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        p.setBrush(QBrush(QColor(91, 141, 239)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(4, 4, 56, 56, 8, 8)
        p.end()
        return QIcon(pixmap)

    def _quit(self):
        if self._closing:
            return
        self._closing = True
        self.tracker.stop()
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        if not self._closing and self.config.get_bool("minimize_to_tray", True):
            self.hide()
            event.ignore()
            return
        self._quit()
````

## File: ui/settings_view.py
````python
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QSpinBox, QDoubleSpinBox,
    QCheckBox, QPushButton, QMessageBox, QGroupBox, QLabel,
)
from PySide6.QtCore import Qt

from services.config_manager import ConfigManager
from services.autostart import enable_autostart, disable_autostart, is_autostart_enabled
from data.repository import Repository
from config import DEFAULT_IDLE_THRESHOLD, DEFAULT_POLL_INTERVAL, DEFAULT_SAVE_TITLES, DEFAULT_MINIMIZE_TO_TRAY
from ui.theme import PALETTE as C


class SettingsView(QWidget):
    def __init__(self, config: ConfigManager, repo: Repository = None,
                 on_settings_changed=None, parent=None):
        super().__init__(parent)
        self.config = config
        self._repo = repo
        self._on_settings_changed = on_settings_changed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Настройки")
        title.setStyleSheet("font-size:20px; font-weight:700;")
        layout.addWidget(title)

        tracking = self._group("Трекинг")
        tf = QFormLayout(tracking)
        tf.setSpacing(12)
        self.idle_spin = QSpinBox()
        self.idle_spin.setRange(1, 60)
        self.idle_spin.setSuffix(" мин")
        self.idle_spin.setValue(
            self.config.get_int("idle_threshold", DEFAULT_IDLE_THRESHOLD) // 60)
        tf.addRow("Порог простоя:", self.idle_spin)
        self.poll_spin = QDoubleSpinBox()
        self.poll_spin.setRange(0.5, 10.0)
        self.poll_spin.setSingleStep(0.5)
        self.poll_spin.setSuffix(" сек")
        self.poll_spin.setValue(
            self.config.get_float("poll_interval", DEFAULT_POLL_INTERVAL))
        tf.addRow("Интервал опроса:", self.poll_spin)
        self.titles_check = QCheckBox()
        self.titles_check.setChecked(
            self.config.get_bool("save_window_titles", DEFAULT_SAVE_TITLES))
        tf.addRow("Сохранять заголовки окон:", self.titles_check)
        layout.addWidget(tracking)

        behavior = self._group("Поведение и система")
        bf = QFormLayout(behavior)
        bf.setSpacing(12)
        self.minimize_check = QCheckBox()
        self.minimize_check.setChecked(
            self.config.get_bool("minimize_to_tray", DEFAULT_MINIMIZE_TO_TRAY))
        bf.addRow("Сворачивать в трей:", self.minimize_check)
        self.autostart_check = QCheckBox()
        self.autostart_check.setChecked(is_autostart_enabled())
        bf.addRow("Автозапуск с Windows:", self.autostart_check)
        layout.addWidget(behavior)

        btn_save = QPushButton("Сохранить")
        btn_save.setObjectName("primary")
        btn_save.clicked.connect(self._save)
        layout.addWidget(btn_save)

        danger = self._group("Опасная зона")
        dl = QVBoxLayout(danger)
        warn = QLabel("Удаление всех данных необратимо.")
        warn.setStyleSheet(f"color:{C.text_muted}; font-size:12px;")
        dl.addWidget(warn)
        btn_clear = QPushButton("Очистить все данные")
        btn_clear.setObjectName("danger")
        btn_clear.clicked.connect(self._clear_data)
        dl.addWidget(btn_clear)
        layout.addWidget(danger)

        layout.addStretch()

    def _group(self, title):
        box = QGroupBox(title)
        return box

    def _save(self):
        self.config.set("idle_threshold", self.idle_spin.value() * 60)
        self.config.set("poll_interval", self.poll_spin.value())
        self.config.set("save_window_titles", self.titles_check.isChecked())
        self.config.set("minimize_to_tray", self.minimize_check.isChecked())
        if self.autostart_check.isChecked():
            enable_autostart()
        else:
            disable_autostart()
        if self._on_settings_changed:
            self._on_settings_changed()
        QMessageBox.information(self, "Настройки", "Настройки сохранены.")

    def _clear_data(self):
        reply = QMessageBox.warning(
            self, "Очистка данных",
            "Вы уверены? Все данные о сессиях и приложениях будут удалены безвозвратно.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes and self._repo:
            self._repo.clear_all_data()
            QMessageBox.information(self, "Очистка", "Все данные удалены.")
````

## File: ui/style.py
````python
from ui.theme import PALETTE as C, RADIUS as R

APP_QSS = f"""
* {{
    font-family: 'Segoe UI', sans-serif;
    color: {C.text};
    outline: none;
}}

QMainWindow, QWidget#root {{
    background-color: {C.bg};
}}

QWidget#sidebar {{
    background-color: {C.sidebar};
    border-right: 1px solid {C.border};
}}

QPushButton#navItem {{
    background: transparent;
    border: none;
    border-radius: {R.md}px;
    padding: 10px 14px;
    text-align: left;
    font-size: 14px;
    color: {C.text_muted};
}}
QPushButton#navItem:hover {{
    background-color: {C.surface_hover};
    color: {C.text};
}}
QPushButton#navItem:checked {{
    background-color: {C.accent_soft};
    color: {C.text};
    font-weight: 600;
}}

QFrame#card {{
    background-color: {C.surface};
    border: 1px solid {C.border};
    border-radius: {R.lg}px;
}}

QTableWidget {{
    background-color: transparent;
    border: none;
    gridline-color: transparent;
    selection-background-color: {C.accent_soft};
    selection-color: {C.text};
}}
QTableWidget::item {{
    padding: 10px 12px;
    border-bottom: 1px solid {C.border};
}}
QHeaderView::section {{
    background: transparent;
    border: none;
    border-bottom: 1px solid {C.border};
    padding: 10px 12px;
    color: {C.text_dim};
    font-size: 12px;
    font-weight: 600;
}}
QTableCornerButton::section {{ background: transparent; border: none; }}

QPushButton {{
    background-color: {C.surface};
    border: 1px solid {C.border};
    border-radius: {R.md}px;
    padding: 9px 18px;
    font-size: 13px;
    color: {C.text};
}}
QPushButton:hover {{
    background-color: {C.surface_hover};
    border-color: {C.accent};
}}
QPushButton#primary {{
    background-color: {C.accent};
    border: none;
    color: white;
    font-weight: 600;
}}
QPushButton#primary:hover {{ background-color: {C.accent_hover}; }}
QPushButton#danger {{
    background-color: transparent;
    border: 1px solid {C.danger};
    color: {C.danger};
}}
QPushButton#danger:hover {{ background-color: {C.danger}; color: white; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {C.bg};
    border: 1px solid {C.border};
    border-radius: {R.md}px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {C.accent};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {C.accent};
}}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    background-color: {C.surface};
    border: 1px solid {C.border};
    border-radius: {R.md}px;
    selection-background-color: {C.accent_soft};
    padding: 4px;
}}

QCheckBox {{ spacing: 8px; font-size: 13px; }}
QCheckBox::indicator {{
    width: 20px; height: 20px;
    border-radius: {R.sm}px;
    border: 1px solid {C.border};
    background: {C.bg};
}}
QCheckBox::indicator:checked {{
    background-color: {C.accent};
    border-color: {C.accent};
}}

QGroupBox {{
    border: 1px solid {C.border};
    border-radius: {R.md}px;
    margin-top: 12px;
    padding: 18px 16px 12px 16px;
    font-weight: 600;
    font-size: 13px;
    color: {C.text_muted};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
}}

QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C.border}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {C.text_dim}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

QStatusBar {{
    background-color: {C.sidebar};
    border-top: 1px solid {C.border};
    color: {C.text_muted};
    font-size: 12px;
}}

QListWidget {{
    background-color: {C.bg};
    border: 1px solid {C.border};
    border-radius: {R.md}px;
}}
QListWidget::item {{
    padding: 4px 8px;
}}
"""
````

## File: ui/theme.py
````python
from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    bg = "#0f1117"
    surface = "#171a21"
    surface_hover = "#1e222b"
    sidebar = "#13151c"
    border = "#252a35"
    text = "#e4e7ec"
    text_muted = "#8b909a"
    text_dim = "#5c616b"
    accent = "#5b8def"
    accent_hover = "#6f9bf2"
    accent_soft = "#1d2740"
    success = "#3ecf8e"
    warning = "#f5a623"
    danger = "#f0616d"
    background_bar = "#3a4150"


@dataclass(frozen=True)
class Spacing:
    xs = 4
    sm = 8
    md = 12
    lg = 16
    xl = 24
    xxl = 32


@dataclass(frozen=True)
class Radius:
    sm = 6
    md = 10
    lg = 14
    pill = 999


PALETTE = Palette()
SPACING = Spacing()
RADIUS = Radius()
FONT_FAMILY = "Segoe UI"


def _fmt(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h} ч {m} мин"
    if m:
        return f"{m} мин {s} сек"
    return f"{s} сек"
````

## File: ui/watchlist_view.py
````python
from typing import Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QListWidget,
    QListWidgetItem, QDialogButtonBox, QFileDialog, QLabel, QLineEdit,
    QStackedWidget, QMenu, QInputDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from services.watchlist import WatchListManager
from data.repository import Repository
from core.process_scanner import list_running_apps
from ui.components.empty_state import EmptyState
from ui.components.app_icons import get_app_icon
from ui.components.app_item_delegate import AppItemDelegate
from ui.theme import _fmt


class AddAppDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить приложение")
        self.setMinimumSize(560, 480)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Выберите из запущенных процессов:"))
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Поиск...")
        self.search_edit.textChanged.connect(self._filter_apps)
        layout.addWidget(self.search_edit)
        self.list_widget = QListWidget(self)
        self.list_widget.setItemDelegate(AppItemDelegate(self.list_widget))
        self.list_widget.setSpacing(2)
        self._all_apps: Dict[str, str] = {}
        self._populate_running_apps()
        layout.addWidget(self.list_widget)
        btn_browse = QPushButton("Обзор... (.exe)", self)
        btn_browse.clicked.connect(self._browse_exe)
        layout.addWidget(btn_browse)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._selected_name = ""
        self._selected_exe = ""

    def _populate_running_apps(self):
        self._all_apps = list_running_apps()
        self._fill(self._all_apps)

    def _fill(self, apps: dict):
        self.list_widget.clear()
        for name, exe in sorted(apps.items()):
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, exe)
            icon = get_app_icon(exe)
            if icon:
                item.setData(Qt.ItemDataRole.DecorationRole, icon)
            self.list_widget.addItem(item)

    def _filter_apps(self, text: str):
        t = text.lower()
        filtered = {
            n: e for n, e in self._all_apps.items()
            if not t or t in n.lower() or t in e.lower()
        }
        self._fill(filtered)

    def _browse_exe(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите исполняемый файл", "", "Executable (*.exe)"
        )
        if path:
            name = path.rsplit("\\", 1)[-1]
            self._selected_name = name
            self._selected_exe = path
            self.accept()

    def selected_app(self):
        it = self.list_widget.currentItem()
        if it:
            self._selected_name = it.text()
            self._selected_exe = it.data(Qt.ItemDataRole.UserRole) or ""
        return self._selected_name, self._selected_exe


class WatchListView(QWidget):
    def __init__(self, watchlist_manager: WatchListManager,
                 repo: Repository = None, on_changed=None, parent=None):
        super().__init__(parent)
        self.manager = watchlist_manager
        self._repo = repo
        self._on_changed = on_changed
        self._current_sort_col = -1
        self._current_sort_order = Qt.SortOrder.AscendingOrder

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Отслеживаемые приложения")
        title.setStyleSheet("font-size:20px; font-weight:700;")
        layout.addWidget(title)

        self._content_stack = QStackedWidget()

        from ui.components.app_icons import asset_pixmap
        self._empty = EmptyState(
            "Список пуст",
            "Добавьте приложения, время которых хотите отслеживать",
            "＋ Добавить приложение", self._on_add,
            pixmap=asset_pixmap("apps.png", 64),
        )
        self._content_stack.addWidget(self._empty)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Приложение", "Процесс", "Путь", "Сегодня"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(1, 160)
        self.table.setColumnWidth(3, 120)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self._content_stack.addWidget(self.table)

        layout.addWidget(self._content_stack, 1)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("＋ Добавить приложение", self)
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self._on_add)
        btn_remove = QPushButton("🗑  Удалить", self)
        btn_remove.clicked.connect(self._on_remove)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.refresh()

    def refresh(self):
        apps = self.manager.get_all()
        today_map = self._repo.get_today_seconds_by_app() if self._repo else {}
        sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)

        if not apps:
            self._content_stack.setCurrentWidget(self._empty)
            return
        self._content_stack.setCurrentWidget(self.table)

        self.table.setRowCount(len(apps))
        for i, app in enumerate(apps):
            display = app.display_name or ""
            icon = get_app_icon(app.exe_path)
            item0 = QTableWidgetItem(display)
            if icon:
                item0.setIcon(icon)
            item0.setData(Qt.ItemDataRole.UserRole, app.id)
            item0.setFlags(item0.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, item0)

            for col, val in [
                (1, app.process_name),
                (2, app.exe_path or ""),
            ]:
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, col, item)

            sec = today_map.get(app.process_name, 0)
            h, m = sec // 3600, (sec % 3600) // 60
            time_text = f"{h} ч {m} мин" if h else f"{m} мин"
            time_item = QTableWidgetItem(time_text)
            time_item.setData(Qt.ItemDataRole.UserRole, sec)
            time_item.setFlags(
                time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 3, time_item)

        self.table.setSortingEnabled(sorting)

    def refresh_times(self):
        if not self._repo:
            return
        today = self._repo.get_today_seconds_by_app()
        for row in range(self.table.rowCount()):
            proc_item = self.table.item(row, 1)
            if not proc_item:
                continue
            sec = today.get(proc_item.text(), 0)
            h, m = sec // 3600, (sec % 3600) // 60
            time_text = f"{h} ч {m} мин" if h else f"{m} мин"
            self.table.item(row, 3).setText(time_text)
            self.table.item(row, 3).setData(Qt.ItemDataRole.UserRole, sec)

    def _on_add(self):
        dlg = AddAppDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, exe = dlg.selected_app()
            if name:
                result = self.manager.add_app(name, exe, name)
                if result == -1:
                    QMessageBox.information(
                        self, "Добавление",
                        f"Приложение «{name}» уже в списке.")
                if self._on_changed:
                    self._on_changed()
                self.refresh()

    def _on_remove(self):
        row = self.table.currentRow()
        if row < 0:
            return
        self._remove_row(row)

    def _remove_row(self, row):
        app_id = self.table.item(row, 0).data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить приложение и всю статистику по нему?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.remove_app(app_id)
            if self._on_changed:
                self._on_changed()
            self.refresh()

    def _rename_row(self, row):
        app_id = self.table.item(row, 0).data(Qt.UserRole)
        current = self.table.item(row, 0).text()
        new, ok = QInputDialog.getText(
            self, "Переименовать",
            "Отображаемое имя:", text=current
        )
        if ok and new.strip() and self._repo:
            self._repo.update_display_name(app_id, new.strip())
            self.refresh()

    def _context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        menu = QMenu(self)
        act_rename = menu.addAction("✎  Переименовать")
        act_delete = menu.addAction("🗑  Удалить")
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_delete:
            self._remove_row(row)
        elif action == act_rename:
            self._rename_row(row)
````

## File: .gitignore
````
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg
*.egg-info/
dist/
build/
*.spec
tracker.db
tracker.db-shm
tracker.db-wal
data/*.db
.env
venv/
.venv/
*.exe

AUDIT.md
PLAN.md
config.json
*.db
*.db-shm
*.db-wal
````

## File: config.py
````python
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
````

## File: main.py
````python
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QStyleFactory

from data.database import Database
from data.repository import Repository
from services.config_manager import ConfigManager
from core.tracker import TrackerService
from ui.main_window import MainWindow
from ui.style import APP_QSS


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RusLOXPy")
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setStyleSheet(APP_QSS)

    db = Database()
    repo = Repository(db)
    config = ConfigManager()

    tracker = TrackerService(repo, config)
    tracker.start()

    window = MainWindow(repo, tracker, config)
    window.show()

    exit_code = app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
````

## File: README.md
````markdown
# RusLOXPy

Отслеживание времени использования выбранных пользователем приложений на **Windows** (только x64).

## Возможности

- Добавление приложений в белый список (из запущенных процессов или выбор .exe вручную)
- Учёт времени только для выбранных приложений
- Определение активного окна через WinAPI
- Статистика за день / неделю / месяц / всё время
- Работа в фоне (сворачивание в трей)
- Автозапуск через реестр
- Настраиваемые: порог простоя, интервал опроса, автостарт

## Технологии

| Компонент  | Библиотека                       |
| ---------- | -------------------------------- |
| GUI        | PySide6 (Qt)                     |
| Процессы   | psutil                           |
| WinAPI     | pywin32 (win32gui, win32process) |
| БД         | sqlite3 (встроенная)             |
| Автозапуск | winreg                           |

## Установка

```bash
pip install -r requirements.txt
```

## Запуск

```bash
python main.py
```

## Сборка в .exe

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name RusLOXPy main.py
```
````

## File: requirements.txt
````
PySide6>=6.6
psutil>=5.9
pywin32>=306
````
