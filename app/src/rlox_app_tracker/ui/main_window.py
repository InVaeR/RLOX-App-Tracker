from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QBrush, QColor, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from rlox_app_tracker.core.tracker import TrackerService
from rlox_app_tracker.data.repository import Repository
from rlox_app_tracker.metadata import PRODUCT_NAME
from rlox_app_tracker.paths import ICON_PATH
from rlox_app_tracker.services.config_manager import ConfigManager
from rlox_app_tracker.services.launcher_bridge import check_updates_interactive, check_updates_silent
from rlox_app_tracker.services.reporter import Reporter
from rlox_app_tracker.services.watchlist import WatchListManager
from rlox_app_tracker.ui.components.app_icons import asset_icon, asset_pixmap
from rlox_app_tracker.ui.components.fade_stack import FadeStack
from rlox_app_tracker.ui.components.pause_banner import PauseBanner
from rlox_app_tracker.ui.dashboard_view import DashboardView
from rlox_app_tracker.ui.settings_view import SettingsView
from rlox_app_tracker.ui.theme import PALETTE as C
from rlox_app_tracker.ui.theme import SPACING as S
from rlox_app_tracker.ui.watchlist_view import WatchListView
from rlox_app_tracker.utils.format import fmt_duration


class NavButton(QPushButton):
    def __init__(self, text, icon_name=""):
        super().__init__(f"  {text}")
        self.setObjectName("navItem")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_name:
            ico = asset_icon(icon_name)
            if not ico.isNull():
                self.setIcon(ico)
                self.setIconSize(QSize(20, 20))


class MainWindow(QMainWindow):
    def __init__(self, repo: Repository, tracker: TrackerService,
                 config: ConfigManager):
        super().__init__()
        self.repo = repo
        self.tracker = tracker
        self.config = config
        self._closing = False
        self._watched_count = len(repo.get_all_watched_apps())

        self.setWindowTitle(PRODUCT_NAME)
        self.setMinimumSize(960, 640)

        watchlist_mgr = WatchListManager(repo)
        reporter = Reporter(repo)

        self.dashboard_view = DashboardView(reporter, on_add_app=self._show_apps)
        self.watchlist_view = WatchListView(watchlist_mgr, repo,
                                            on_changed=self._on_watchlist_changed)
        self.settings_view = SettingsView(config, repo,
            on_settings_changed=self._on_settings_changed,
            on_data_cleared=self._on_data_cleared)

        root = QWidget()
        root.setObjectName("root")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(S.md, S.xl, S.md, S.lg)
        sb.setSpacing(S.xs)

        logo_pix = asset_pixmap("real-time.png", 24)
        logo_row = QWidget()
        logo_row_layout = QHBoxLayout(logo_row)
        logo_row_layout.setContentsMargins(14, 8, 14, 20)
        logo_icon = QLabel()
        if not logo_pix.isNull():
            logo_icon.setPixmap(logo_pix)
        logo_text = QLabel(PRODUCT_NAME)
        logo_text.setStyleSheet(
            "font-size:18px; font-weight:700;")
        logo_row_layout.addWidget(logo_icon)
        logo_row_layout.addWidget(logo_text)
        logo_row_layout.addStretch()
        sb.addWidget(logo_row)

        self.nav_group = QButtonGroup(self)
        self.btn_dash = NavButton("Дашборд", "stats.png")
        self.btn_apps = NavButton("Приложения", "apps.png")
        self.btn_settings = NavButton("Настройки", "setting.png")
        for i, b in enumerate(
            [self.btn_dash, self.btn_apps, self.btn_settings]
        ):
            self.nav_group.addButton(b, i)
            sb.addWidget(b)
        sb.addStretch()

        self.status_dot = QLabel("● Отслеживание активно")
        self.status_dot.setStyleSheet(
            f"color:{C.success}; font-size:12px; padding:8px 14px;")
        sb.addWidget(self.status_dot)

        self.stack = FadeStack()
        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.watchlist_view)
        self.stack.addWidget(self.settings_view)

        self.pause_banner = PauseBanner()
        content_col = QVBoxLayout()
        content_col.setContentsMargins(0, 0, 0, 0)
        content_col.setSpacing(0)
        content_col.addWidget(self.pause_banner)
        content_col.addWidget(self.stack, 1)

        layout.addWidget(sidebar)
        layout.addLayout(content_col, 1)
        self.setCentralWidget(root)

        self.nav_group.idClicked.connect(self._on_nav)
        self.btn_dash.setChecked(True)

        for i, key in enumerate(("Ctrl+1", "Ctrl+2", "Ctrl+3")):
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(lambda idx=i: self._nav_to(idx))

        self.setStatusBar(QStatusBar())
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status)
        self._status_timer.start(5000)
        self._refresh_status()

        self._live_refresh = QTimer(self)
        self._live_refresh.timeout.connect(self._on_live_refresh)
        self._live_refresh.start(5000)

        self._setup_tray()

        self.tracker.stats_updated.connect(self.dashboard_view.refresh)
        self.tracker.active_app_info.connect(self.dashboard_view.update_live)
        self.tracker.active_app_info.connect(self._update_tray_tooltip)
        self.tracker.tracking_paused.connect(self._on_tracking_paused)
        self.tracker.tracking_resumed.connect(self._on_tracking_resumed)
        self.pause_banner.resume_clicked.connect(self.tracker.resume)

        if self.config.get_bool("check_updates_on_start", True):
            QTimer.singleShot(3000, self._check_update_startup)

    def _check_update_startup(self):
        check_updates_silent()

    def _manual_check_update(self):
        from PySide6.QtWidgets import QMessageBox
        if not check_updates_interactive():
            QMessageBox.information(
                self, "Проверка обновлений",
                "Лаунчер не найден. Обновления можно проверить только через установленную версию программы.")

    def _nav_to(self, idx: int):
        self.nav_group.button(idx).setChecked(True)
        self.stack.setCurrentIndex(idx)

    def _on_nav(self, idx: int):
        self.stack.setCurrentIndex(idx)

    def _show_apps(self):
        self.btn_apps.setChecked(True)
        self.stack.setCurrentIndex(1)

    def _on_data_cleared(self):
        self.tracker.reset_all(emit=False)
        self.repo.clear_all_data()
        self._watched_count = 0
        self.dashboard_view.refresh()
        self.dashboard_view.update_live({"paused": self.tracker.is_paused,
                                         "running_apps": [], "focused": None,
                                         "focused_display": "", "focused_sec": 0})
        self.watchlist_view.refresh()

    def _on_settings_changed(self):
        self.tracker.update_settings()

    def _on_watchlist_changed(self):
        self.tracker.invalidate_cache()
        self._watched_count = len(self.repo.get_all_watched_apps())

    def _on_tracking_paused(self):
        self._pause_action.setChecked(True)
        self.status_dot.setText("● Пауза")
        self.status_dot.setStyleSheet(
            f"color:{C.warning}; font-size:12px; padding:8px 14px;")
        self.pause_banner.show()

    def _on_tracking_resumed(self):
        self._pause_action.setChecked(False)
        self.status_dot.setText("● Отслеживание активно")
        self.status_dot.setStyleSheet(
            f"color:{C.success}; font-size:12px; padding:8px 14px;")
        self.pause_banner.hide()

    def _refresh_status(self):
        if self.tracker.is_paused:
            self.statusBar().showMessage("Отслеживание приостановлено")
        else:
            self.statusBar().showMessage(
                f"Отслеживается приложений: {self._watched_count}")

    def _on_live_refresh(self):
        if self.stack.currentWidget() is self.dashboard_view:
            self.dashboard_view.refresh()
        elif self.stack.currentWidget() is self.watchlist_view:
            self.watchlist_view.refresh_times()

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip(PRODUCT_NAME)
        icon = self._load_icon()
        self.setWindowIcon(icon)
        tray_menu = QMenu(self)
        show_action = QAction("Показать", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)
        self._pause_action = QAction("Пауза", self)
        self._pause_action.setCheckable(True)
        self._pause_action.triggered.connect(self._toggle_pause)
        tray_menu.addAction(self._pause_action)
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self._quit)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def _update_tray_tooltip(self, info: dict):
        if info.get("paused"):
            self.tray_icon.setToolTip(f"{PRODUCT_NAME} — пауза")
        elif info.get("focused"):
            name = info.get("focused_display") or info.get("focused")
            sec = info.get("focused_sec", 0)
            self.tray_icon.setToolTip(
                f"{PRODUCT_NAME} — {name} · {fmt_duration(sec, short=True)}")
        else:
            self.tray_icon.setToolTip(PRODUCT_NAME)

    def _toggle_pause(self, checked):
        if checked:
            self.tracker.pause()
        else:
            self.tracker.resume()

    def _load_icon(self) -> QIcon:
        if ICON_PATH.exists():
            return QIcon(str(ICON_PATH))
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        p.setBrush(QBrush(QColor(91, 141, 239)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(4, 4, 56, 56, 8, 8)
        p.end()
        return QIcon(pixmap)

    def _quit(self):
        if self._closing:
            return
        self._closing = True
        self.tracker.stop()
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        if not self._closing and self.config.get_bool("minimize_to_tray", True):
            self.hide()
            event.ignore()
            return
        self._quit()
