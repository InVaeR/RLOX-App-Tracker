"""
RLOX Launcher — точка входа в RLOX App Tracker.

Команды:
    --launch                  Запустить приложение (по умолчанию)
    --launch --background     Запустить в фоне
    --check-updates           Проверить обновления
    --check-updates --interactive  Интерактивная проверка
    --repair                  Восстановить установку
    --version                 Показать версию лаунчера
"""
import sys
import os
import argparse
import json
import hashlib
import logging
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from logging.handlers import RotatingFileHandler

LAUNCHER_VERSION = "1.0.0"
PRODUCT_NAME = "RLOX App Tracker"
SINGLETON_KEY = "RLOXAppTracker.Launcher"
REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

_local_app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
_data_root = _local_app_data / PRODUCT_NAME
_install_root = _local_app_data / "Programs" / PRODUCT_NAME
STATE_DIR = _install_root / "state"
UPDATES_DIR = _data_root / "updates" / "downloads"
LOG_DIR = _data_root / "logs"
INSTALL_JSON = STATE_DIR / "install.json"
APP_EXE = "RLOXAppTracker.exe"
LAUNCHER_EXE = "RLOXLauncher.exe"
MANIFEST_URL = "https://github.com/InVaeR/RLOX-App-Tracker/releases/latest/download/latest.json"
SETUP_NAME = "RLOX-App-Tracker-Setup-x64.exe"

for d in [STATE_DIR, UPDATES_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

_logger = logging.getLogger("launcher")


def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] launcher: %(message)s")
    fh = RotatingFileHandler(LOG_DIR / "launcher.log", maxBytes=2*1024*1024, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    if "--interactive" in sys.argv:
        root.addHandler(sh)


LAUNCHER_CONFIG_PATH = _data_root / "config" / "launcher.json"


@dataclass
class LauncherConfig:
    channel: str = "stable"
    check_on_launch: bool = True
    auto_download: bool = True
    auto_install: bool = False
    check_interval_hours: int = 12
    skipped_version: str = ""
    last_check_at: str = ""

    @classmethod
    def load(cls) -> "LauncherConfig":
        if LAUNCHER_CONFIG_PATH.exists():
            try:
                data = json.loads(LAUNCHER_CONFIG_PATH.read_text(encoding="utf-8"))
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except (json.JSONDecodeError, OSError):
                _logger.warning("launcher config повреждён")
        return cls()

    def save(self):
        LAUNCHER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = LAUNCHER_CONFIG_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps({
            "channel": self.channel,
            "checkOnLaunch": self.check_on_launch,
            "autoDownload": self.auto_download,
            "autoInstall": self.auto_install,
            "checkIntervalHours": self.check_interval_hours,
            "skippedVersion": self.skipped_version,
            "lastCheckAt": self.last_check_at,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(LAUNCHER_CONFIG_PATH)


@dataclass
class InstallState:
    current_version: str = ""
    previous_version: str = ""
    channel: str = "stable"
    app_executable: str = ""

    @classmethod
    def load(cls) -> "InstallState":
        if INSTALL_JSON.exists():
            try:
                data = json.loads(INSTALL_JSON.read_text(encoding="utf-8"))
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except (json.JSONDecodeError, OSError):
                _logger.warning("install.json повреждён")
        return cls()

    def save(self):
        INSTALL_JSON.parent.mkdir(parents=True, exist_ok=True)
        tmp = INSTALL_JSON.with_suffix(".tmp")
        tmp.write_text(json.dumps({
            "currentVersion": self.current_version,
            "previousVersion": self.previous_version,
            "channel": self.channel,
            "appExecutable": self.app_executable,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(INSTALL_JSON)


@dataclass
class UpdateManifest:
    version: str = ""
    installer_url: str = ""
    sha256: str = ""
    size: int = 0
    mandatory: bool = False
    release_notes_url: str = ""

    @classmethod
    def fetch(cls, timeout: float = 5.0) -> Optional["UpdateManifest"]:
        try:
            req = urllib.request.Request(MANIFEST_URL, headers={
                "Accept": "application/json",
                "User-Agent": "RLOXLauncher/1.0",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            inst = data.get("installer", {})
            return cls(
                version=data.get("version", ""),
                installer_url=inst.get("url", ""),
                sha256=inst.get("sha256", ""),
                size=inst.get("size", 0),
                mandatory=data.get("mandatory", False),
                release_notes_url=data.get("releaseNotesUrl", ""),
            )
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as e:
            _logger.warning("Не удалось получить манифест: %s", e)
            return None


def _parse_version(v: str) -> tuple:
    v = v.lstrip("v").split("-")[0]
    parts = []
    for x in v.split("."):
        try:
            parts.append(int(x))
        except ValueError:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def find_app_exe(install: InstallState) -> Optional[Path]:
    if install.app_executable:
        exe = _install_root / install.app_executable
        if exe.exists():
            return exe
    versions_dir = _install_root / "versions"
    if not versions_dir.exists():
        return None
    versions = sorted(
        [d for d in versions_dir.iterdir() if d.is_dir()],
        key=lambda d: _parse_version(d.name), reverse=True
    )
    for ver_dir in versions:
        exe = ver_dir / APP_EXE
        if exe.exists():
            return exe
    return None


def launch_app(background: bool = False) -> bool:
    install = InstallState.load()
    exe = find_app_exe(install)
    if not exe:
        _logger.error("Приложение не найдено")
        return False
    cmd = [str(exe)]
    if background:
        cmd.append("--background")
    _logger.info("Запуск: %s", " ".join(cmd))
    try:
        subprocess.Popen(cmd, shell=False)
        return True
    except OSError as e:
        _logger.error("Ошибка запуска: %s", e)
        return False


def check_updates(interactive: bool = False):
    install = InstallState.load()
    if not install.current_version:
        _logger.info("Приложение не установлено")
        if interactive:
            print("Приложение не установлено. Запустите установщик.")
        return

    manifest = UpdateManifest.fetch()
    if manifest is None:
        if interactive:
            print("Не удалось проверить обновления (нет сети или ошибка сервера).")
        return

    if _parse_version(manifest.version) > _parse_version(install.current_version):
        _logger.info("Доступно обновление: %s", manifest.version)
        if interactive:
            print(f"Доступна версия {manifest.version} (текущая: {install.current_version})")
            if manifest.release_notes_url:
                print(f"Примечания: {manifest.release_notes_url}")
            choice = input("Установить обновление? (y/N): ").strip().lower()
            if choice == "y":
                download_and_install(manifest, install)
        else:
            download_and_install(manifest, install)
    else:
        _logger.info("Установлена последняя версия: %s", install.current_version)
        if interactive:
            print(f"Установлена последняя версия: {install.current_version}")


def download_and_install(manifest: UpdateManifest, install: InstallState):
    if not manifest.installer_url:
        _logger.error("URL установщика пуст")
        return

    setup_path = UPDATES_DIR / f"{manifest.version}" / SETUP_NAME
    part_path = setup_path.with_suffix(".part")
    part_path.parent.mkdir(parents=True, exist_ok=True)

    _logger.info("Скачивание %s -> %s", manifest.installer_url, part_path)
    try:
        req = urllib.request.Request(manifest.installer_url, headers={
            "User-Agent": "RLOXLauncher/1.0",
        })
        with urllib.request.urlopen(req) as r:
            with open(part_path, "wb") as f:
                shasum = hashlib.sha256()
                while True:
                    chunk = r.read(64 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    shasum.update(chunk)
        actual_sha = shasum.hexdigest().lower()
        expected_sha = manifest.sha256.lower()
        if expected_sha and actual_sha != expected_sha:
            _logger.error("SHA-256 не совпадает: ожидался %s, получен %s", expected_sha, actual_sha)
            part_path.unlink(missing_ok=True)
            return
        part_path.rename(setup_path)
        _logger.info("Установщик скачан и проверен")
    except (urllib.error.URLError, OSError) as e:
        _logger.error("Ошибка скачивания: %s", e)
        return

    _logger.info("Запуск установщика: %s", setup_path)
    try:
        subprocess.run(
            [str(setup_path), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/UPDATE"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        _logger.error("Установщик завершился с ошибкой: %s", e)
    except OSError as e:
        _logger.error("Не удалось запустить установщик: %s", e)


def repair():
    _logger.info("Запуск восстановления")
    install = InstallState.load()
    if not install.current_version:
        _logger.error("Нет установленной версии для восстановления")
        return
    exe = find_app_exe(install)
    if exe:
        _logger.info("Приложение найдено: %s", exe)
        launch_app()
    else:
        _logger.error("Приложение не найдено. Переустановите программу.")


def enable_autostart():
    import winreg
    launcher_path = _install_root / LAUNCHER_EXE
    if not launcher_path.exists():
        _logger.error("Лаунчер не найден: %s", launcher_path)
        return False
    cmd = f'"{launcher_path}" --launch --background'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, PRODUCT_NAME, 0, winreg.REG_SZ, cmd)
        return True
    except OSError as e:
        _logger.error("Ошибка автозапуска: %s", e)
        return False


def disable_autostart():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as k:
            try:
                winreg.DeleteValue(k, PRODUCT_NAME)
            except FileNotFoundError:
                pass
        return True
    except OSError as e:
        _logger.error("Ошибка отключения автозапуска: %s", e)
        return False


def is_autostart_enabled() -> bool:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, PRODUCT_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="RLOXLauncher")
    parser.add_argument("--launch", action="store_true", help="Запустить приложение")
    parser.add_argument("--background", action="store_true", help="Запуск в фоне")
    parser.add_argument("--check-updates", action="store_true", help="Проверить обновления")
    parser.add_argument("--interactive", action="store_true", help="Интерактивный режим")
    parser.add_argument("--silent", action="store_true", help="Тихий режим")
    parser.add_argument("--repair", action="store_true", help="Восстановление")
    parser.add_argument("--shutdown", action="store_true", help="Завершить приложение")
    parser.add_argument("--version", action="store_true", help="Версия лаунчера")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    setup_logging()

    if args.version:
        print(f"RLOXLauncher v{LAUNCHER_VERSION}")
        return

    _logger.info("Запуск лаунчера: %s", " ".join(sys.argv[1:] if argv is None else argv or []))

    if args.shutdown:
        _send_ipc("shutdown")
        return

    if args.repair:
        repair()
        return

    if args.check_updates:
        check_updates(interactive=args.interactive or args.silent is False)
        return

    launch_app(background=args.background or False)


def _send_ipc(command: str):
    try:
        from rlox_app_tracker.__main__ import SingleInstance
        si = SingleInstance()
        if not si.send_command(command):
            _logger.warning("Приложение не запущено или IPC недоступен")
    except ImportError:
        _logger.warning("Модуль приложения не найден, отправка IPC через QLocalSocket")
        from PySide6.QtNetwork import QLocalSocket
        from PySide6.QtCore import QCoreApplication
        app = QCoreApplication(sys.argv)
        sock = QLocalSocket()
        sock.connectToServer("RLOXAppTracker.Application")
        if sock.waitForConnected(300):
            sock.write((command + "\n").encode())
            sock.waitForBytesWritten(500)
            sock.disconnectFromServer()
            sock.close()


if __name__ == "__main__":
    main()
