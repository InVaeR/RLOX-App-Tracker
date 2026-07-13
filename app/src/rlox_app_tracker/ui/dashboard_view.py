from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rlox_app_tracker.data.models import AppStats
from rlox_app_tracker.services.reporter import Reporter
from rlox_app_tracker.ui.components.app_icons import asset_pixmap, get_app_icon
from rlox_app_tracker.ui.components.bar_chart import ChartContainer
from rlox_app_tracker.ui.components.empty_state import EmptyState
from rlox_app_tracker.ui.components.legend import Legend
from rlox_app_tracker.ui.components.stat_card import StatCard
from rlox_app_tracker.ui.theme import PALETTE as C
from rlox_app_tracker.ui.theme import SPACING as S
from rlox_app_tracker.utils.format import fmt_duration
from rlox_app_tracker.utils.pixmap import tint_pixmap


class NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        return (self.data(Qt.ItemDataRole.UserRole) or 0) < \
               (other.data(Qt.ItemDataRole.UserRole) or 0)


class LiveCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        ll = QHBoxLayout(self)
        ll.setContentsMargins(16, 14, 16, 14)

        pulse_pix = asset_pixmap("point.png", 16)
        self._pulse = QLabel()
        if not pulse_pix.isNull():
            self._pulse.setPixmap(tint_pixmap(QPixmap(pulse_pix), C.success))
        else:
            self._pulse.setText("●")
            self._pulse.setStyleSheet(f"color:{C.success}; font-size:14px;")
        eff = QGraphicsOpacityEffect(self._pulse)
        self._pulse.setGraphicsEffect(eff)
        self._anim = QPropertyAnimation(eff, b"opacity")
        self._anim.setDuration(1200)
        self._anim.setStartValue(1.0)
        self._anim.setKeyValueAt(0.5, 0.3)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.start()

        texts = QVBoxLayout()
        texts.setSpacing(2)
        self._live_name = QLabel("Ожидание…")
        self._live_name.setStyleSheet(
            f"font-size:15px; font-weight:600; color:{C.text};")
        self._live_detail = QLabel("Нет активного приложения")
        self._live_detail.setStyleSheet(
            f"font-size:12px; color:{C.text_muted};")
        texts.addWidget(self._live_name)
        texts.addWidget(self._live_detail)

        self._live_timer = QLabel("00:00")
        self._live_timer.setStyleSheet(
            f"font-size:20px; font-weight:700; color:{C.accent};")

        ll.addWidget(self._pulse)
        ll.addLayout(texts, 1)
        ll.addWidget(self._live_timer)

    def _tint_pulse(self, color: str):
        pulse_pix = asset_pixmap("point.png", 16)
        if not pulse_pix.isNull():
            self._pulse.setPixmap(tint_pixmap(QPixmap(pulse_pix), color))
        else:
            self._pulse.setStyleSheet(f"color:{color}; font-size:14px;")

    def update_info(self, info: dict):
        if not info or info.get("paused"):
            self._live_name.setText("Трекинг приостановлен")
            self._live_detail.setText("Нажмите «Возобновить» в меню трея")
            self._live_timer.setText("—")
            self._tint_pulse(C.warning)
            return

        focused = info.get("focused")
        background = info.get("background_apps", [])

        if focused:
            display_name = info.get("focused_display") or focused
            sec = info.get("focused_sec", 0)
            self._live_name.setText(display_name)
            if background:
                bg_names = ", ".join(
                    a.get("display_name", a["name"]) for a in background[:4])
                self._live_detail.setText(f"Активно · В фоне: {bg_names}")
            else:
                self._live_detail.setText("Активное окно")
            self._live_timer.setText(fmt_duration(sec))
            self._tint_pulse(C.success)
        elif background:
            names = ", ".join(
                a.get("display_name", a["name"]) for a in background[:5])
            self._live_name.setText(f"В фоне: {len(background)}")
            self._live_detail.setText(names)
            self._live_timer.setText("—")
            self._tint_pulse(C.text_dim)
        else:
            self._live_name.setText("Ожидание…")
            self._live_detail.setText("Нет запущенных отслеживаемых приложений")
            self._live_timer.setText("—")
            self._tint_pulse(C.text_dim)


class DashboardView(QWidget):
    _PERIOD_LABELS = {
        0: "сегодня",
        1: "за неделю",
        2: "за месяц",
        3: "за всё время",
    }

    def __init__(self, reporter: Reporter, on_add_app=None, parent=None):
        super().__init__(parent)
        self.reporter = reporter
        self._on_add_app = on_add_app
        self._stats: list[AppStats] = []
        self._running_now = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        content = QWidget()
        content.setObjectName("dashContent")
        content.setStyleSheet(f"#dashContent {{ background: {C.bg}; }}")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(S.xl, S.xl, S.xl, S.xl)
        layout.setSpacing(S.lg)

        self.live_card = LiveCard()
        layout.addWidget(self.live_card)

        cards_row = QGridLayout()
        cards_row.setSpacing(S.md)
        self.card_total = StatCard("Всего за период", C.accent)
        self.card_active = StatCard("Активное время", C.success)
        self.card_background = StatCard("Фоновое время", C.warning)
        self.card_running = StatCard("Запущено сейчас", C.text_muted)
        self.card_top = StatCard("Топ приложение", C.text)
        for i, card in enumerate(
            [self.card_total, self.card_active, self.card_background]
        ):
            cards_row.addWidget(card, 0, i)
        for i, card in enumerate([self.card_running, self.card_top]):
            cards_row.addWidget(card, 1, i)
        layout.addLayout(cards_row)

        period_row = QHBoxLayout()
        period_row.setContentsMargins(0, 0, 0, 0)
        period_label = QLabel("Период:")
        period_label.setStyleSheet(
            f"color:{C.text_muted}; font-size:12px; font-weight:600;")
        period_row.addWidget(period_label)
        self.period_combo = QComboBox()
        self.period_combo.addItems(
            ["Сегодня", "Неделя", "Месяц", "За всё время"])
        self.period_combo.currentIndexChanged.connect(self._on_period_change)
        period_row.addWidget(self.period_combo)
        period_row.addStretch()
        self._btn_export = QPushButton("Экспорт CSV")
        self._btn_export.clicked.connect(self._export_csv)
        period_row.addWidget(self._btn_export)
        layout.addLayout(period_row)

        self._chart_container = ChartContainer()
        layout.addWidget(self._chart_container)

        self._legend = Legend()
        layout.addWidget(self._legend)

        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("dashContentStack")
        self._content_stack.setStyleSheet(f"#dashContentStack {{ background: {C.bg}; }}")
        self._empty = EmptyState(
            "Нет данных",
            "Запустите отслеживаемое приложение, чтобы увидеть статистику",
            button_text="＋ Добавить приложение" if on_add_app else "",
            on_click=on_add_app,
            pixmap=asset_pixmap("stats.png", 64),
        )
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["Приложение", "Активное", "Фоновое", "Сессий"])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(1, 120)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(2, 120)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(3, 65)
        self._table.setAlternatingRowColors(False)
        self._table.setShowGrid(False)
        self._table.verticalHeader().hide()
        self._table.setSortingEnabled(True)
        self._content_stack.addWidget(self._table)
        self._content_stack.addWidget(self._empty)
        layout.addWidget(self._content_stack, 1)

        scroll.setWidget(content)
        root.addWidget(scroll)

        self.refresh()

    def update_live(self, info: dict):
        self.live_card.update_info(info)
        self._running_now = len(info.get("running_apps", []))
        self.card_running.set_value(str(self._running_now))

    def refresh(self):
        idx = self.period_combo.currentIndex()
        if idx == 0:
            stats = self.reporter.get_daily_stats()
        elif idx == 1:
            stats = self.reporter.get_weekly_stats()
        elif idx == 2:
            stats = self.reporter.get_monthly_stats()
        else:
            stats = self.reporter.get_all_time_stats()
        self._stats = stats
        self._update_contents(stats)

    def _on_period_change(self):
        self.refresh()

    def _export_csv(self):
        if not self._stats:
            return
        period = self.period_combo.currentText().replace(" ", "_").lower()
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт статистики",
            f"rusloxpy_{period}.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            self.reporter.export_csv(self._stats, path)
        except OSError as e:
            QMessageBox.warning(
                self, "Экспорт",
                f"Не удалось сохранить файл:\n{e}\n\n"
                "Возможно, файл открыт в другой программе.")
            return
        self._btn_export.setText("✓ Экспортировано")
        self._btn_export.setEnabled(False)
        QTimer.singleShot(1500, self._restore_export_btn)

    def _restore_export_btn(self):
        self._btn_export.setText("Экспорт CSV")
        self._btn_export.setEnabled(True)

    def _update_contents(self, stats):
        stats_with_data = [
            s for s in stats
            if s.active_seconds + s.background_seconds > 0
        ]
        has_data = bool(stats_with_data)
        self._chart_container.setVisible(has_data)
        self._legend.setVisible(has_data)
        if has_data:
            self._chart_container.set_stats(stats)
        self._update_cards(stats)
        self._update_table(stats)

    def _update_cards(self, stats):
        total = sum(s.active_seconds + s.background_seconds for s in stats)
        active = sum(s.active_seconds for s in stats)
        background = total - active
        idx = self.period_combo.currentIndex()
        period_label = self._PERIOD_LABELS.get(idx, "")
        self.card_total.set_title(f"Всего {period_label}")
        self.card_total.set_value(fmt_duration(total))
        self.card_active.set_value(
            fmt_duration(active),
            f"{int(active / total * 100) if total else 0}%",
        )
        self.card_background.set_value(
            fmt_duration(background),
            f"{int(background / total * 100) if total else 0}%",
        )
        self.card_running.set_value(str(self._running_now))
        top = max(
            stats,
            key=lambda s: s.active_seconds + s.background_seconds,
            default=None,
        )
        if top and (top.active_seconds + top.background_seconds) > 0:
            self.card_top.set_value(
                top.display_name or top.process_name,
                fmt_duration(top.active_seconds + top.background_seconds),
            )
        else:
            self.card_top.set_value("—", "")

    def _update_table(self, stats):
        stats_with_data = [
            s for s in stats
            if s.active_seconds + s.background_seconds > 0
        ]
        if not stats_with_data:
            self._content_stack.setCurrentWidget(self._empty)
            return
        self._content_stack.setCurrentWidget(self._table)

        sorting = self._table.isSortingEnabled()
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(stats_with_data))
        for i, s in enumerate(stats_with_data):
            name = s.display_name or s.process_name
            name_item = QTableWidgetItem(name)
            icon = get_app_icon(s.exe_path) if s.exe_path else None
            if icon:
                name_item.setIcon(icon)
            name_item.setData(Qt.ItemDataRole.UserRole, name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 0, name_item)

            for col, val, raw in [
                (1, fmt_duration(s.active_seconds), s.active_seconds),
                (2, fmt_duration(s.background_seconds), s.background_seconds),
                (3, str(s.session_count), s.session_count),
            ]:
                item = NumericItem(val)
                item.setData(Qt.ItemDataRole.UserRole, raw)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(i, col, item)
        self._table.setSortingEnabled(sorting)
