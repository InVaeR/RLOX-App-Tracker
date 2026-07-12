import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QStyleFactory

from data.database import Database
from data.repository import Repository
from services.config_manager import ConfigManager
from core.tracker import TrackerService
from ui.main_window import MainWindow
from ui.style import APP_QSS


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RusLOXPy")
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setStyleSheet(APP_QSS)

    db = Database()
    repo = Repository(db)
    config = ConfigManager()

    tracker = TrackerService(repo, config)
    tracker.start()

    window = MainWindow(repo, tracker, config)
    window.show()

    exit_code = app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
