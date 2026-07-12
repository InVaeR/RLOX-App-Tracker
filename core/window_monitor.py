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
