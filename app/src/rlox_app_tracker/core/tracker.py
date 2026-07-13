import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from rlox_app_tracker.core.idle_detector import get_idle_seconds
from rlox_app_tracker.core.process_scanner import get_running_process_names
from rlox_app_tracker.core.window_monitor import get_active_window_process
from rlox_app_tracker.data.models import Session, WatchedApp
from rlox_app_tracker.data.repository import Repository
from rlox_app_tracker.defaults import DEFAULT_IDLE_THRESHOLD, DEFAULT_POLL_INTERVAL
from rlox_app_tracker.services.config_manager import ConfigManager


@dataclass
class _SessionState:
    session_id: int
    start_time: datetime
    title: str
    active_sec: int = 0
    background_sec: int = 0
    _acc: float = 0.0


@dataclass
class _TickContext:
    now: datetime
    delta: float
    slept: bool
    idle_now: float
    focused_name: Optional[str]
    focused_app_id: Optional[int]
    focused_display: str
    focused_sec: int
    running_names: set
    watched_apps: List[WatchedApp]
    watched_ids: Dict[int, WatchedApp]
    watched_running: List[dict]
    background_apps: List[dict]
    window: Optional[dict]


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
        self._last_tick_monotonic: Optional[float] = None
        self._tick_count = 0
        self._watched_cache: List[WatchedApp] = []
        self._cache_dirty = True
        self._last_known_date: Optional[str] = None
        self._load_settings()

    def _load_settings(self):
        self._poll_interval = max(0.5, min(10.0, self.config.get_float("poll_interval", DEFAULT_POLL_INTERVAL)))
        self._idle_threshold = self.config.get_int("idle_threshold", DEFAULT_IDLE_THRESHOLD)
        self._save_titles = self.config.get_bool("save_window_titles", True)

    def start(self):
        self.repo.close_all_active_sessions()
        self._sessions.clear()
        self._running = True
        self._paused = False
        self._last_tick_monotonic = time.monotonic()
        self._last_known_date = datetime.now().date().isoformat()
        self._timer.start(int(self._poll_interval * 1000))

    def stop(self):
        self._running = False
        self._close_all_sessions()
        self._timer.stop()

    def pause(self):
        if self._paused:
            return
        self._paused = True
        self._close_all_sessions()
        self._last_tick_monotonic = None
        self._emit_paused_info()
        self.tracking_paused.emit()

    def resume(self):
        if not self._paused:
            return
        self._paused = False
        self._last_tick_monotonic = time.monotonic()
        self.tracking_resumed.emit()

    def _emit_paused_info(self):
        self.active_app_info.emit(
            {
                "paused": True,
                "running_apps": [],
                "background_apps": [],
                "focused": None,
                "focused_display": "",
                "focused_sec": 0,
            }
        )

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

    def _compute_delta(self) -> tuple:
        slept = False
        delta = self._poll_interval
        now_mono = time.monotonic()
        if self._last_tick_monotonic is not None:
            elapsed = now_mono - self._last_tick_monotonic
            max_gap = max(self._poll_interval * 3, 10)
            slept = elapsed > max_gap
            if slept:
                delta = 0
            else:
                delta = min(elapsed, self._poll_interval * 2)
        self._last_tick_monotonic = now_mono
        return delta, slept

    def _collect_context(self, now: datetime, delta: float, slept: bool) -> _TickContext:
        idle_now = get_idle_seconds()
        window = get_active_window_process()
        focused_name = window["name"] if window else None
        running_names = get_running_process_names()
        watched_apps = self._get_watched_apps()
        watched_ids = {a.id: a for a in watched_apps if a.id}

        watched_running = [{"name": a.process_name, "display_name": a.display_name or a.process_name} for a in watched_apps if a.process_name in running_names]
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

        focused_set = {focused_name} if focused_app_id is not None else set()
        background_apps = [
            {"name": a.process_name, "display_name": a.display_name or a.process_name}
            for a in watched_apps
            if a.process_name in running_names and a.process_name not in focused_set
        ]

        return _TickContext(
            now=now,
            delta=delta,
            slept=slept,
            idle_now=idle_now,
            focused_name=focused_name,
            focused_app_id=focused_app_id,
            focused_display=focused_display,
            focused_sec=focused_sec,
            running_names=running_names,
            watched_apps=watched_apps,
            watched_ids=watched_ids,
            watched_running=watched_running,
            background_apps=background_apps,
            window=window,
        )

    def _update_sessions(self, ctx: _TickContext):
        for app in ctx.watched_apps:
            if app.id is None:
                continue
            is_running = app.process_name in ctx.running_names
            is_focused = ctx.focused_name == app.process_name
            state = self._sessions.get(app.id)

            if not is_running:
                if state:
                    self._close_session(app.id, state)
                continue

            if not state:
                title = ctx.window["title"] if is_focused and self._save_titles else ""
                sess = Session(app_id=app.id, start_time=ctx.now, window_title=title)
                sid = self.repo.add_session(sess)
                self._sessions[app.id] = _SessionState(session_id=sid, start_time=ctx.now, title=title)

            state = self._sessions[app.id]
            delta_int = int(ctx.delta)
            state._acc += ctx.delta - delta_int
            if state._acc >= 1.0:
                extra = int(state._acc)
                delta_int += extra
                state._acc -= extra

            if delta_int > 0:
                if is_focused and ctx.idle_now <= self._idle_threshold:
                    state.active_sec += delta_int
                    if self._save_titles and ctx.window:
                        state.title = ctx.window["title"]
                else:
                    state.background_sec += delta_int

    def _cleanup_orphan_sessions(self, ctx: _TickContext):
        for app_id, state in list(self._sessions.items()):
            if app_id not in ctx.watched_ids:
                self._close_session(app_id, state)

    def _emit_live_info(self, ctx: _TickContext):
        self.active_app_info.emit(
            {
                "paused": self._paused,
                "running_apps": ctx.watched_running,
                "background_apps": ctx.background_apps,
                "focused": ctx.focused_name if ctx.focused_app_id is not None else None,
                "focused_display": ctx.focused_display,
                "focused_sec": ctx.focused_sec,
            }
        )

    def _check_day_boundary(self, now: datetime):
        today = now.date().isoformat()
        if self._last_known_date is not None and self._last_known_date != today:
            self._close_all_sessions()
        self._last_known_date = today

    def _tick(self):
        if self._paused:
            return

        self._tick_count += 1
        now = datetime.now()

        self._check_day_boundary(now)

        delta, slept = self._compute_delta()

        if slept:
            self._close_all_sessions()

        ctx = self._collect_context(now, delta, slept)
        self._update_sessions(ctx)
        self._cleanup_orphan_sessions(ctx)
        self._emit_live_info(ctx)
        self._periodic_flush()

    def reset_all(self, emit=True):
        self._sessions.clear()
        self._cache_dirty = True
        self._watched_cache = []
        if emit:
            self.stats_updated.emit()

    def _close_session(self, app_id: int, state: _SessionState, emit=True):
        now = datetime.now()
        elapsed = max(0, int((now - state.start_time).total_seconds()))
        active = min(max(0, state.active_sec), elapsed)
        background = min(max(0, state.background_sec), max(0, elapsed - active))
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
        if emit:
            self.stats_updated.emit()

    def _close_all_sessions(self):
        for app_id, state in list(self._sessions.items()):
            self._close_session(app_id, state, emit=False)
        self.stats_updated.emit()

    def _periodic_flush(self):
        if self._tick_count % 10 != 0:
            return
        now = datetime.now()
        for app_id, state in self._sessions.items():
            elapsed = max(0, int((now - state.start_time).total_seconds()))
            active = min(max(0, state.active_sec), elapsed)
            background = min(max(0, state.background_sec), max(0, elapsed - active))
            self.repo.flush_session(
                state.session_id,
                active + background,
                active,
                background,
                state.title,
            )
