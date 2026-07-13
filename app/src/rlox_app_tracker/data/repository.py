from datetime import datetime
from typing import List, Optional

from rlox_app_tracker.data.database import Database
from rlox_app_tracker.data.models import AppStats, Session, WatchedApp


class Repository:
    def __init__(self, db: Database):
        self.db = db

    def add_watched_app(self, app: WatchedApp) -> int:
        cur = self.db.execute(
            "INSERT OR IGNORE INTO watched_apps (process_name, display_name, exe_path) VALUES (?, ?, ?)",
            (app.process_name, app.display_name, app.exe_path),
        )
        self.db.commit()
        if cur.rowcount == 0:
            row = self.db.execute("SELECT id FROM watched_apps WHERE process_name = ?", (app.process_name,)).fetchone()
            return row["id"] if row else 0
        return cur.lastrowid or 0

    def remove_watched_app(self, app_id: int):
        self.db.execute("DELETE FROM watched_apps WHERE id = ?", (app_id,))
        self.db.commit()

    def get_all_watched_apps(self) -> List[WatchedApp]:
        rows = self.db.execute("SELECT * FROM watched_apps ORDER BY added_at").fetchall()
        return [WatchedApp(**dict(r)) for r in rows]

    def get_watched_app_by_name(self, name: str) -> Optional[WatchedApp]:
        row = self.db.execute("SELECT * FROM watched_apps WHERE process_name = ?", (name,)).fetchone()
        return WatchedApp(**dict(row)) if row else None

    def is_watched(self, process_name: str) -> bool:
        row = self.db.execute("SELECT 1 FROM watched_apps WHERE process_name = ?", (process_name,)).fetchone()
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
            "UPDATE sessions SET end_time = ?, duration_sec = ?, active_sec = ?, "
            "background_sec = ?, window_title = COALESCE(?, window_title), last_seen_at = ? WHERE id = ?",  # noqa: E501
            (session.end_time, session.duration_sec, session.active_sec, session.background_sec, session.window_title, session.end_time, session.id),
        )
        self.db.commit()

    def flush_session(self, session_id: int, duration_sec: int, active_sec: int, background_sec: int, title: str = None):
        now = datetime.now()
        if title:
            self.db.execute(
                "UPDATE sessions SET duration_sec = ?, active_sec = ?, background_sec = ?, window_title = ?, last_seen_at = ? WHERE id = ?",
                (duration_sec, active_sec, background_sec, title, now, session_id),
            )
        else:
            self.db.execute(
                "UPDATE sessions SET duration_sec = ?, active_sec = ?, background_sec = ?, last_seen_at = ? WHERE id = ?",
                (duration_sec, active_sec, background_sec, now, session_id),
            )
        self.db.commit()

    def close_all_active_sessions(self):
        self.db.execute(
            "UPDATE sessions SET end_time = COALESCE(last_seen_at, ?), "
            "duration_sec = COALESCE(active_sec,0) + COALESCE(background_sec,0) WHERE end_time IS NULL",
            (datetime.now(),),
        )
        self.db.commit()

    def get_stats(self, period_days: int = 1) -> List[AppStats]:
        time_filter = ""
        params = ()
        if period_days is None:
            pass
        elif period_days == 1:
            time_filter = "AND s.start_time >= datetime('now', 'localtime', 'start of day')"
        else:
            days_offset = period_days - 1
            time_filter = "AND s.start_time >= datetime('now', 'localtime', 'start of day', ?)"
            params = (f"-{days_offset} days",)

        query = f"""
            SELECT w.process_name, w.display_name, w.exe_path,
                   COALESCE(SUM(s.active_sec), 0) as active_seconds,
                   COALESCE(SUM(s.background_sec), 0) as background_seconds,
                   COUNT(s.id) as session_count
            FROM watched_apps w
            LEFT JOIN sessions s ON s.app_id = w.id
                {time_filter}
            GROUP BY w.id
            ORDER BY active_seconds + background_seconds DESC
        """
        rows = self.db.execute(query, params).fetchall()
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
        self.db.execute("UPDATE watched_apps SET display_name = ? WHERE id = ?", (name, app_id))
        self.db.commit()

    def clear_all_data(self):
        self.db.execute("DELETE FROM sessions")
        self.db.execute("DELETE FROM watched_apps")
        self.db.commit()
