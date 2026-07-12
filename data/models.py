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


@dataclass
class AppStats:
    process_name: str
    display_name: str
    active_seconds: int
    background_seconds: int
    session_count: int
    exe_path: Optional[str] = None
