"""
LauncherBridge — интерфейс между приложением и RLOXLauncher.

Приложение не должно напрямую проверять обновления или управлять установкой.
Все операции с обновлениями делегируются лаунчеру.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _find_launcher() -> Optional[Path]:
    import sys

    from rlox_app_tracker.paths import APP_DIR, INSTALL_DIR

    candidates = [
        INSTALL_DIR / "RLOXLauncher.exe",
        APP_DIR / "RLOXLauncher.exe",
        APP_DIR.parent / "RLOXLauncher.exe",
        Path(sys.executable).parent / "RLOXLauncher.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def launch_launcher(args: list[str]) -> bool:
    launcher = _find_launcher()
    if not launcher:
        logger.warning("Лаунчер не найден, пропускаем: %s", " ".join(args))
        return False
    try:
        subprocess.Popen([str(launcher)] + args, shell=False)
        return True
    except OSError as e:
        logger.error("Ошибка запуска лаунчера: %s", e)
        return False


def check_updates_silent() -> bool:
    return launch_launcher(["--check-updates", "--silent"])


def check_updates_interactive() -> bool:
    return launch_launcher(["--check-updates", "--interactive"])


def launch_background() -> bool:
    return launch_launcher(["--launch", "--background"])


def repair() -> bool:
    return launch_launcher(["--repair"])


def is_launcher_available() -> bool:
    return _find_launcher() is not None
