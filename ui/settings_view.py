from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QSpinBox, QDoubleSpinBox,
    QCheckBox, QPushButton, QMessageBox, QGroupBox, QLabel,
)
from PySide6.QtCore import Qt

from services.config_manager import ConfigManager
from services.autostart import enable_autostart, disable_autostart, is_autostart_enabled
from data.repository import Repository
from config import DEFAULT_IDLE_THRESHOLD, DEFAULT_POLL_INTERVAL, DEFAULT_SAVE_TITLES, DEFAULT_MINIMIZE_TO_TRAY
from ui.theme import PALETTE as C


class SettingsView(QWidget):
    def __init__(self, config: ConfigManager, repo: Repository = None,
                 on_settings_changed=None, parent=None):
        super().__init__(parent)
        self.config = config
        self._repo = repo
        self._on_settings_changed = on_settings_changed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Настройки")
        title.setStyleSheet("font-size:20px; font-weight:700;")
        layout.addWidget(title)

        tracking = self._group("Трекинг")
        tf = QFormLayout(tracking)
        tf.setSpacing(12)
        self.idle_spin = QSpinBox()
        self.idle_spin.setRange(1, 60)
        self.idle_spin.setSuffix(" мин")
        self.idle_spin.setValue(
            self.config.get_int("idle_threshold", DEFAULT_IDLE_THRESHOLD) // 60)
        tf.addRow("Порог простоя:", self.idle_spin)
        self.poll_spin = QDoubleSpinBox()
        self.poll_spin.setRange(0.5, 10.0)
        self.poll_spin.setSingleStep(0.5)
        self.poll_spin.setSuffix(" сек")
        self.poll_spin.setValue(
            self.config.get_float("poll_interval", DEFAULT_POLL_INTERVAL))
        tf.addRow("Интервал опроса:", self.poll_spin)
        self.titles_check = QCheckBox()
        self.titles_check.setChecked(
            self.config.get_bool("save_window_titles", DEFAULT_SAVE_TITLES))
        tf.addRow("Сохранять заголовки окон:", self.titles_check)
        layout.addWidget(tracking)

        behavior = self._group("Поведение и система")
        bf = QFormLayout(behavior)
        bf.setSpacing(12)
        self.minimize_check = QCheckBox()
        self.minimize_check.setChecked(
            self.config.get_bool("minimize_to_tray", DEFAULT_MINIMIZE_TO_TRAY))
        bf.addRow("Сворачивать в трей:", self.minimize_check)
        self.autostart_check = QCheckBox()
        self.autostart_check.setChecked(is_autostart_enabled())
        bf.addRow("Автозапуск с Windows:", self.autostart_check)
        layout.addWidget(behavior)

        btn_save = QPushButton("Сохранить")
        btn_save.setObjectName("primary")
        btn_save.clicked.connect(self._save)
        layout.addWidget(btn_save)

        danger = self._group("Опасная зона")
        dl = QVBoxLayout(danger)
        warn = QLabel("Удаление всех данных необратимо.")
        warn.setStyleSheet(f"color:{C.text_muted}; font-size:12px;")
        dl.addWidget(warn)
        btn_clear = QPushButton("Очистить все данные")
        btn_clear.setObjectName("danger")
        btn_clear.clicked.connect(self._clear_data)
        dl.addWidget(btn_clear)
        layout.addWidget(danger)

        layout.addStretch()

    def _group(self, title):
        box = QGroupBox(title)
        return box

    def _save(self):
        self.config.set("idle_threshold", self.idle_spin.value() * 60)
        self.config.set("poll_interval", self.poll_spin.value())
        self.config.set("save_window_titles", self.titles_check.isChecked())
        self.config.set("minimize_to_tray", self.minimize_check.isChecked())
        if self.autostart_check.isChecked():
            enable_autostart()
        else:
            disable_autostart()
        if self._on_settings_changed:
            self._on_settings_changed()
        QMessageBox.information(self, "Настройки", "Настройки сохранены.")

    def _clear_data(self):
        reply = QMessageBox.warning(
            self, "Очистка данных",
            "Вы уверены? Все данные о сессиях и приложениях будут удалены безвозвратно.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes and self._repo:
            self._repo.clear_all_data()
            QMessageBox.information(self, "Очистка", "Все данные удалены.")
