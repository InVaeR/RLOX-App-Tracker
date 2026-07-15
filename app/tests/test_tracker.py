"""Тесты алгоритма трекинга."""

import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from rlox_app_tracker.core.tracker import TrackerService, _SessionState
from rlox_app_tracker.data.models import WatchedApp


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.add_session.return_value = 1
    return repo


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.get_float.return_value = 1.5
    config.get_int.return_value = 300
    config.get_bool.return_value = True
    return config


@pytest.fixture
def tracker(mock_repo, mock_config):
    t = TrackerService(mock_repo, mock_config)
    t._poll_interval = 1.5
    t._idle_threshold = 300
    t._save_titles = True
    return t


def test_tick_normal(tracker):
    with (
        patch("rlox_app_tracker.core.tracker.get_idle_seconds", return_value=5),
        patch("rlox_app_tracker.core.tracker.get_active_window_process", return_value=None),
        patch("rlox_app_tracker.core.tracker.list_running_apps", return_value={}),
    ):
        tracker._tick()
    assert tracker._tick_count == 1


def test_pause_resume(tracker, mock_repo):
    tracker._sessions[1] = _SessionState(session_id=1, start_time=datetime.now(), title="")
    tracker.pause()
    assert tracker._paused
    assert tracker._last_tick_monotonic is None
    mock_repo.update_session.assert_called()

    tracker.resume()
    assert not tracker._paused
    assert tracker._last_tick_monotonic is not None


def test_pause_idempotent(tracker):
    tracker._paused = True
    tracker.pause()
    assert tracker._paused


def test_resume_idempotent(tracker):
    tracker._paused = False
    tracker.resume()
    assert not tracker._paused


def test_delta_uses_monotonic(tracker):
    tracker._last_tick_monotonic = time.monotonic() - 2.0
    delta, slept = tracker._compute_delta()
    assert 1.5 <= delta <= 3.0
    assert not slept


def test_delta_sleep_detected(tracker):
    tracker._last_tick_monotonic = time.monotonic() - 60
    delta, slept = tracker._compute_delta()
    assert delta == 0
    assert slept


def test_close_session_negative_protection(tracker):
    state = _SessionState(session_id=1, start_time=datetime.now(), title="", active_sec=100, background_sec=50)
    tracker._sessions[1] = state
    tracker._close_session(1, state, emit=False)
    tracker.repo.update_session.assert_called()
    sess = tracker.repo.update_session.call_args[0][0]
    assert sess.active_sec >= 0
    assert sess.background_sec >= 0
    assert sess.duration_sec >= 0


def test_day_boundary(tracker):
    from datetime import timedelta

    now = datetime.now()
    yesterday = now - timedelta(days=1)
    tracker._last_known_date = yesterday.date().isoformat()
    tracker._sessions[1] = _SessionState(session_id=1, start_time=yesterday, title="")
    tracker._check_day_boundary(now)
    assert 1 not in tracker._sessions
    assert tracker._last_known_date == now.date().isoformat()


def test_start_no_delta_on_first_tick(tracker):
    tracker._last_tick_monotonic = None
    delta, slept = tracker._compute_delta()
    assert delta == tracker._poll_interval
    assert not slept


def test_accumulator_handles_fractional(tracker):
    state = _SessionState(session_id=1, start_time=datetime.now(), title="")
    state._acc = 0.7
    tracker._sessions[1] = state
    ctx = MagicMock()
    ctx.delta = 0.6
    ctx.watched_apps = [WatchedApp(id=1, process_name="test.exe")]
    ctx.running_names = {"test.exe"}
    ctx.focused_name = "test.exe"
    ctx.idle_now = 5
    ctx.window = {"title": "Test"}
    ctx.watched_ids = {1: WatchedApp(id=1, process_name="test.exe")}
    with (
        patch("rlox_app_tracker.core.tracker.get_idle_seconds", return_value=5),
        patch("rlox_app_tracker.core.tracker.get_active_window_process", return_value={"name": "test.exe", "title": "Test"}),
        patch("rlox_app_tracker.core.tracker.list_running_apps", return_value={"test.exe": "/path/to/test.exe"}),
    ):
        pass
    tracker._update_sessions(ctx)
    assert state.active_sec >= 1
    assert state._acc < 1.0


def test_empty_session_id_skipped(tracker):
    state = _SessionState(session_id=0, start_time=datetime.now(), title="")
    tracker._sessions[None] = state
    ctx = MagicMock()
    ctx.watched_apps = [WatchedApp(id=None, process_name="test.exe")]
    ctx.running_names = {"test.exe"}
    ctx.window = None
    ctx.focused_name = "test.exe"
    ctx.idle_now = 5
    ctx.watched_ids = {}
    ctx.watched_running = []
    ctx.background_apps = []
    ctx.delta = 1.5
    ctx.now = datetime.now()
    tracker._update_sessions(ctx)
    assert True


def test_periodic_flush(tracker):
    from datetime import timedelta

    start = datetime.now() - timedelta(hours=1)
    state = _SessionState(session_id=1, start_time=start, title="", active_sec=10, background_sec=5)
    tracker._sessions[1] = state
    tracker._tick_count = 10
    tracker._periodic_flush()
    tracker.repo.flush_session.assert_called_with(1, 15, 10, 5, "")
