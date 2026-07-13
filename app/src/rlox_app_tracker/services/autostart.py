import logging
import sys
import winreg

from rlox_app_tracker.metadata import AUTOSTART_VALUE
from rlox_app_tracker.paths import LAUNCHER_PATH

logger = logging.getLogger(__name__)

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _autostart_cmd() -> str:
    if getattr(sys, "frozen", False):
        return f'"{LAUNCHER_PATH}" --launch --background'
    return f'"{sys.executable}" -m rlox_app_tracker --background'


def enable_autostart(app_name: str = AUTOSTART_VALUE):
    cmd = _autostart_cmd()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, app_name, 0, winreg.REG_SZ, cmd)
    except OSError as e:
        logger.error("Не удалось включить автозапуск: %s", e)
        raise


def disable_autostart(app_name: str = AUTOSTART_VALUE):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as k:
            try:
                winreg.DeleteValue(k, app_name)
            except FileNotFoundError:
                pass
    except OSError as e:
        logger.error("Не удалось отключить автозапуск: %s", e)
        raise


def is_autostart_enabled(app_name: str = AUTOSTART_VALUE) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as k:
            value, _ = winreg.QueryValueEx(k, app_name)
            return value == _autostart_cmd()
    except FileNotFoundError:
        return False
    except OSError:
        return False
