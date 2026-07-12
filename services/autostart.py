import sys
import winreg

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def enable_autostart(app_name: str = "RusLOXPy"):
    path = sys.executable
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, app_name, 0, winreg.REG_SZ, f'"{path}"')


def disable_autostart(app_name: str = "RusLOXPy"):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as k:
        try:
            winreg.DeleteValue(k, app_name)
        except FileNotFoundError:
            pass


def is_autostart_enabled(app_name: str = "RusLOXPy") -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, app_name)
            return True
    except FileNotFoundError:
        return False
