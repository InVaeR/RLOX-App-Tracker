import argparse
import json
import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox, QStyleFactory

from rlox_app_tracker.core.tracker import TrackerService
from rlox_app_tracker.data.database import Database
from rlox_app_tracker.data.repository import Repository
from rlox_app_tracker.metadata import APP_EXE_NAME, PRODUCT_NAME, SINGLETON_KEY_APP
from rlox_app_tracker.migration import migrate, needs_migration
from rlox_app_tracker.paths import DATA_DIR, STATE_DIR
from rlox_app_tracker.services.config_manager import ConfigManager
from rlox_app_tracker.ui.main_window import MainWindow
from rlox_app_tracker.ui.style import APP_QSS
from rlox_app_tracker.utils.logger import setup_logging
from rlox_app_tracker.version import __version__

logger = logging.getLogger(__name__)

_IPC_COMMANDS = {"show", "shutdown", "shutdown-for-update", "ping"}


class SingleInstance(QObject):
    def __init__(self, key: str = SINGLETON_KEY_APP):
        super().__init__()
        self._key = key
        self._server = None
        self._on_show = None
        self._on_shutdown = None

    def on_show(self, callback):
        self._on_show = callback

    def on_shutdown(self, callback):
        self._on_shutdown = callback

    def try_acquire(self):
        sock = QLocalSocket()
        sock.connectToServer(self._key)
        if sock.waitForConnected(300):
            sock.write(b"show\n")
            sock.waitForBytesWritten(500)
            sock.disconnectFromServer()
            sock.close()
            return "already_running"
        QLocalServer.removeServer(self._key)
        server = QLocalServer()
        server.setSocketOptions(QLocalServer.SocketOption.WorldAccessOption)
        if not server.listen(self._key):
            logger.error("Не удалось занять singleton-сокет: %s", server.errorString())
            return "error"
        server.newConnection.connect(self._on_new_connection)
        self._server = server
        return "ok"

    def _on_new_connection(self):
        sock = self._server.nextPendingConnection()
        if not sock:
            return
        if sock.waitForReadyRead(1000):
            data = sock.readAll().data().decode("utf-8", errors="replace").strip()
            logger.info("IPC команда: %s", data)
            if data == "show" and self._on_show:
                self._on_show()
            elif data == "shutdown" and self._on_shutdown:
                self._on_shutdown()
            elif data == "shutdown-for-update" and self._on_shutdown:
                self._on_shutdown()
            elif data == "ping":
                sock.write(b"pong\n")
                sock.waitForBytesWritten(200)
        sock.disconnectFromServer()
        sock.deleteLater()

    def send_command(self, command: str) -> bool:
        if command not in _IPC_COMMANDS:
            logger.warning("Неизвестная IPC команда: %s", command)
            return False
        sock = QLocalSocket()
        sock.connectToServer(self._key)
        if not sock.waitForConnected(300):
            return False
        sock.write((command + "\n").encode())
        ok = sock.waitForBytesWritten(500)
        if command == "ping":
            if sock.waitForReadyRead(500):
                response = sock.readAll().data().decode()
                ok = response.strip() == "pong"
        sock.disconnectFromServer()
        sock.close()
        return ok

    @property
    def server(self):
        return self._server


def write_startup_marker():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    marker = STATE_DIR / f"startup-ok-{__version__}"
    marker.write_text(
        json.dumps(
            {
                "version": __version__,
                "pid": os.getpid(),
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }
        ),
        encoding="utf-8",
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog=APP_EXE_NAME)
    parser.add_argument("--background", action="store_true", help="Запуск в фоне (трей)")
    parser.add_argument("--minimized", action="store_true", help="Запуск свёрнутым")
    parser.add_argument("--after-update", action="store_true", help="Запуск после обновления")
    parser.add_argument("--data-dir", type=str, help="Путь к каталогу данных")
    parser.add_argument("--version", action="store_true", help="Показать версию")
    parser.add_argument("--ipc", type=str, choices=list(_IPC_COMMANDS), help="Отправить IPC команду")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.version:
        print(f"{PRODUCT_NAME} v{__version__}")
        sys.exit(0)

    if args.ipc:
        si = SingleInstance()
        success = si.send_command(args.ipc)
        sys.exit(0 if success else 1)

    setup_logging()
    logger.info("Запуск %s v%s", PRODUCT_NAME, __version__)

    app = QApplication(sys.argv)
    app.setApplicationName(PRODUCT_NAME)
    app.setApplicationVersion(__version__)
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setStyleSheet(APP_QSS)

    si = SingleInstance()
    result = si.try_acquire()

    if result == "already_running":
        logger.warning("Приложение уже запущено — активируем окно")
        sys.exit(0)

    if result == "error":
        QMessageBox.critical(None, PRODUCT_NAME, "Не удалось запустить приложение: ошибка singleton-механизма.\n\nПопробуйте перезапустить приложение.")
        os._exit(1)

    data_dir = Path(args.data_dir) if args.data_dir else DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "tracker.db"

    if needs_migration():
        logger.info("Обнаружены данные RusLOXPy, запуск миграции...")
        migrate()
        logger.info("Миграция завершена")

    db = Database(db_path=db_path)
    repo = Repository(db)
    config = ConfigManager()

    tracker = TrackerService(repo, config)
    window = MainWindow(repo, tracker, config)

    si.on_shutdown(lambda: _shutdown(app))
    si.on_show(lambda: _show_window(window))

    def cleanup():
        logger.info("Shutdown: останов трекера и БД")
        try:
            tracker.stop()
        finally:
            db.close()

    app.aboutToQuit.connect(cleanup)

    tracker.start()

    if args.background:
        window.hide()
        logger.info("Запуск в фоне (трей)")
    elif args.minimized:
        window.showMinimized()
    else:
        window.show()

    write_startup_marker()
    logger.info("Startup marker создан")

    exit_code = app.exec()
    si.server.close()
    logger.info("Завершение (code=%s)", exit_code)
    sys.exit(exit_code)


def _show_window(window: MainWindow):
    window.showNormal()
    window.activateWindow()
    window.raise_()


def _shutdown(app):
    app.quit()


if __name__ == "__main__":
    main()
