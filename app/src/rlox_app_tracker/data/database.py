import datetime
import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from rlox_app_tracker.paths import DB_PATH

logger = logging.getLogger(__name__)


def _adapt_datetime(dt: datetime.datetime) -> str:
    return dt.isoformat()


def _convert_datetime(s: bytes) -> datetime.datetime:
    return datetime.datetime.fromisoformat(s.decode("utf-8"))


sqlite3.register_adapter(datetime.datetime, _adapt_datetime)
sqlite3.register_converter("datetime", _convert_datetime)
sqlite3.register_converter("timestamp", _convert_datetime)


class Database:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DB_PATH
        self.lock = threading.Lock()
        self.conn: sqlite3.Connection = None
        self._closed = False
        self._connect()
        self._migrate()

    def _connect(self):
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA busy_timeout = 5000")

    def _backup(self):
        backup_path = self.db_path.with_suffix(".db.backup")
        try:
            conn = sqlite3.connect(str(backup_path))
            self.conn.backup(conn)
            conn.close()
            logger.info("Резервная копия БД: %s", backup_path)
        except Exception as e:
            logger.warning("Не удалось создать резервную копию БД: %s", e)

    def _migrate(self):
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)")
        row = cur.execute("SELECT version FROM schema_version").fetchone()
        current = row["version"] if row else 0

        migrations = [self._m001_initial, self._m002_active_bg, self._m003_indexes, self._m004_last_seen]
        if current < len(migrations):
            self._backup()

        for i, migration in enumerate(migrations, start=1):
            if current >= i:
                continue
            try:
                self.conn.execute("BEGIN")
                migration(cur)
                cur.execute("DELETE FROM schema_version")
                cur.execute("INSERT INTO schema_version (version) VALUES (?)", (i,))
                self.conn.commit()
                current = i
            except Exception:
                self.conn.rollback()
                logger.error("Миграция БД #%s не удалась", i)
                raise

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
                FOREIGN KEY (app_id) REFERENCES watched_apps(id) ON DELETE CASCADE
            );
        """)

    def _m002_active_bg(self, cur):
        existing = [r["name"] for r in cur.execute("PRAGMA table_info(sessions)").fetchall()]
        for col in ("active_sec", "background_sec"):
            if col not in existing:
                cur.execute(f"ALTER TABLE sessions ADD COLUMN {col} INTEGER DEFAULT 0")

    def _m003_indexes(self, cur):
        cur.executescript("""
            CREATE INDEX IF NOT EXISTS idx_sessions_app_id
            ON sessions(app_id);

            CREATE INDEX IF NOT EXISTS idx_sessions_start_time
            ON sessions(start_time);

            CREATE INDEX IF NOT EXISTS idx_sessions_app_start
            ON sessions(app_id, start_time);
        """)

    def _m004_last_seen(self, cur):
        existing = [r["name"] for r in cur.execute("PRAGMA table_info(sessions)").fetchall()]
        if "last_seen_at" not in existing:
            cur.execute("ALTER TABLE sessions ADD COLUMN last_seen_at DATETIME")

    def execute(self, sql: str, params=()):
        with self.lock:
            return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_seq):
        with self.lock:
            return self.conn.executemany(sql, params_seq)

    def commit(self):
        with self.lock:
            self.conn.commit()

    @contextmanager
    def transaction(self):
        with self.lock:
            try:
                self.conn.execute("BEGIN")
                yield self.conn
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def close(self):
        if self._closed:
            return
        with self.lock:
            if self._closed:
                return
            self._closed = True
            self.conn.close()
