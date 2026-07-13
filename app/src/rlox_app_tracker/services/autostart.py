import sys
import logging
import winreg

from rlox_app_tracker.metadata import AUTOSTART_VALUE as __app_name__

logger = logging.getLogger(__name__)

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def enable_autostart(app_name: str = __app_name__):
    path = sys.executable
    script = ""
    if getattr(sys, "frozen", False):
        cmd = f'"{path}"'
    else:
        script = __import__("__main__").__file__
        cmd = f'"{path}" "{script}"'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, app_name, 0, winreg.REG_SZ, cmd)
    except OSError as e:
        logger.error("Не удалось включить автозапуск: %s", e)
        raise


def disable_autostart(app_name: str = __app_name__):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as k:
            try:
                winreg.DeleteValue(k, app_name)
            except FileNotFoundError:
                pass
    except OSError as e:
        logger.error("Не удалось отключить автозапуск: %s", e)
        raise


def is_autostart_enabled(app_name: str = __app_name__) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as k:
            value, _ = winreg.QueryValueEx(k, app_name)
            path = sys.executable
            if getattr(sys, "frozen", False):
                expected = f'"{path}"'
            else:
                script = __import__("__main__").__file__
                expected = f'"{path}" "{script}"'
            return value == expected
    except FileNotFoundError:
        return False
    except OSError:
        return False
