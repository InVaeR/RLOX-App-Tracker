import logging
from typing import Dict, Optional

import psutil
import win32gui
import win32process

logger = logging.getLogger(__name__)


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
    except Exception:
        logger.exception("get_active_window_process")
        return None
