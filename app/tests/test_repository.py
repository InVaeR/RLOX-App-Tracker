"""Тесты репозитория с временной БД."""
from pathlib import Path

import pytest
from rlox_app_tracker.data.database import Database
from rlox_app_tracker.data.models import Session, WatchedApp
from rlox_app_tracker.data.repository import Repository


@pytest.fixture
def db(tmp_path: Path):
    return Database(tmp_path / "test.db")


@pytest.fixture
def repo(db):
    return Repository(db)


def test_add_watched_app(repo):
    app = WatchedApp(process_name="test.exe", display_name="Test", exe_path="C:\\test.exe")
    app_id = repo.add_watched_app(app)
    assert app_id > 0


def test_add_watched_app_duplicate(repo):
    app = WatchedApp(process_name="test.exe")
    repo.add_watched_app(app)
    app2 = WatchedApp(process_name="test.exe")
    app_id2 = repo.add_watched_app(app2)
    assert app_id2 > 0


def test_get_all_watched_apps(repo):
    repo.add_watched_app(WatchedApp(process_name="a.exe"))
    repo.add_watched_app(WatchedApp(process_name="b.exe"))
    apps = repo.get_all_watched_apps()
    assert len(apps) == 2


def test_remove_watched_app(repo):
    app_id = repo.add_watched_app(WatchedApp(process_name="test.exe"))
    repo.remove_watched_app(app_id)
    apps = repo.get_all_watched_apps()
    assert len(apps) == 0


def test_add_session(repo):
    app_id = repo.add_watched_app(WatchedApp(process_name="test.exe"))
    sess = Session(app_id=app_id, start_time="2026-01-01 00:00:00")
    sess_id = repo.add_session(sess)
    assert sess_id > 0


def test_update_session(repo):
    app_id = repo.add_watched_app(WatchedApp(process_name="test.exe"))
    sess_id = repo.add_session(Session(app_id=app_id, start_time="2026-01-01 00:00:00"))
    repo.update_session(Session(
        id=sess_id, end_time="2026-01-01 01:00:00",
        duration_sec=3600, active_sec=1800, background_sec=1800,
    ))
    rows = repo.db.execute("SELECT * FROM sessions WHERE id = ?", (sess_id,)).fetchall()
    assert len(rows) == 1
    assert rows[0]["duration_sec"] == 3600


def test_flush_session(repo):
    app_id = repo.add_watched_app(WatchedApp(process_name="test.exe"))
    sess_id = repo.add_session(Session(app_id=app_id, start_time="2026-01-01 00:00:00"))
    repo.flush_session(sess_id, 100, 60, 40)
    rows = repo.db.execute("SELECT * FROM sessions WHERE id = ?", (sess_id,)).fetchall()
    assert rows[0]["duration_sec"] == 100


def test_close_all_active_sessions(repo):
    app_id = repo.add_watched_app(WatchedApp(process_name="test.exe"))
    repo.add_session(Session(app_id=app_id, start_time="2026-01-01 00:00:00"))
    repo.close_all_active_sessions()
    rows = repo.db.execute("SELECT * FROM sessions WHERE end_time IS NULL").fetchall()
    assert len(rows) == 0


def test_get_stats_empty(repo):
    stats = repo.get_stats(period_days=1)
    assert len(stats) == 0


def test_get_stats_with_data(repo):
    app_id = repo.add_watched_app(WatchedApp(process_name="test.exe"))
    repo.add_session(Session(app_id=app_id, start_time="2026-01-01 00:00:00", active_sec=100, background_sec=50, duration_sec=150))
    stats = repo.get_stats(period_days=None)
    assert len(stats) == 1
    assert stats[0].active_seconds == 100
    assert stats[0].background_seconds == 50


def test_get_today_seconds_by_app(repo):
    app_id = repo.add_watched_app(WatchedApp(process_name="test.exe"))
    repo.add_session(Session(app_id=app_id, start_time="2026-01-01 00:00:00", active_sec=200, background_sec=100, duration_sec=300))
    result = repo.get_today_seconds_by_app()
    assert isinstance(result, dict)


def test_clear_all_data(repo):
    repo.add_watched_app(WatchedApp(process_name="test.exe"))
    repo.add_session(Session(app_id=1, start_time="2026-01-01 00:00:00"))
    repo.clear_all_data()
    assert len(repo.get_all_watched_apps()) == 0
    stats = repo.get_stats(period_days=None)
    assert len(stats) == 0


def test_update_display_name(repo):
    app_id = repo.add_watched_app(WatchedApp(process_name="test.exe", display_name="Old"))
    repo.update_display_name(app_id, "New")
    apps = repo.get_all_watched_apps()
    assert apps[0].display_name == "New"


def test_get_watched_app_by_name(repo):
    repo.add_watched_app(WatchedApp(process_name="test.exe"))
    app = repo.get_watched_app_by_name("test.exe")
    assert app is not None
    assert app.process_name == "test.exe"


def test_is_watched(repo):
    repo.add_watched_app(WatchedApp(process_name="test.exe"))
    assert repo.is_watched("test.exe")
    assert not repo.is_watched("other.exe")
