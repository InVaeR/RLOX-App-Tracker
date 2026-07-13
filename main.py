import sys
import os
import logging

from PySide6.QtWidgets import QApplication, QStyleFactory, QMessageBox
from PySide6.QtNetwork import QLocalSocket, QLocalServer

from data.database import Database
from data.repository import Repository
from services.config_manager import ConfigManager
from core.tracker import TrackerService
from ui.main_window import MainWindow
from ui.style import APP_QSS
from config import APP_NAME, APP_VERSION
from utils.logger import setup_logging

logger = logging.getLogger(__name__)

_SINGLETON_KEY = "RusLOXPy_singleton"


def acquire_single_instance():
    sock = QLocalSocket()
    sock.connectToServer(_SINGLETON_KEY)
    if sock.waitForConnected(300):
        sock.disconnectFromServer()
        sock.close()
        return "already_running"
    QLocalServer.removeServer(_SINGLETON_KEY)
    server = QLocalServer()
    if not server.listen(_SINGLETON_KEY):
        logger.error(
            "Не удалось занять singleton-сокет: %s",
            server.errorString(),
        )
        return "error"
    return server


def main():
    setup_logging()
    logger.info("Запуск %s v%s", APP_NAME, APP_VERSION)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setStyleSheet(APP_QSS)

    result = acquire_single_instance()
    if result == "already_running":
        logger.warning("Приложение уже запущено — выход")
        QMessageBox.information(
            None, APP_NAME,
            f"{APP_NAME} уже запущен.\n\n"
            "В системе может быть только один экземпляр приложения."
        )
        os._exit(0)
    elif result == "error":
        QMessageBox.critical(
            None, APP_NAME,
            "Не удалось запустить приложение: ошибка singleton-механизма.\n\n"
            f"Попробуйте перезапустить {APP_NAME}."
        )
        os._exit(1)

    server = result
    app._single_instance_server = server # type: ignore

    db = Database()
    repo = Repository(db)
    config = ConfigManager()

    tracker = TrackerService(repo, config)

    def cleanup():
        logger.info("Cleanup: останов трекера и БД")
        try:
            tracker.stop()
        finally:
            db.close()

    app.aboutToQuit.connect(cleanup)

    tracker.start()

    window = MainWindow(repo, tracker, config)
    window.show()

    exit_code = app.exec()
    server.close()
    logger.info("Завершение (code=%s)", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
