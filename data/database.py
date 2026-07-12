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
        self.conn.execute("PRAGMA synchronous=NORMAL")

    def _migrate(self):
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)")
        row = cur.execute("SELECT version FROM schema_version").fetchone()
        current = row["version"] if row else 0

        migrations = [self._m001_initial, self._m002_active_bg]
        for i, migration in enumerate(migrations, start=1):
            if current < i:
                migration(cur)
                current = i

        cur.execute("DELETE FROM schema_version")
        cur.execute("INSERT INTO schema_version (version) VALUES (?)", (current,))
        self.conn.commit()

    def _m001_initial(self, cur):
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

    def _m002_active_bg(self, cur):
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
