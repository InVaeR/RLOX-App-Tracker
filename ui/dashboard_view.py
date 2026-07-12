from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QComboBox,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QGraphicsOpacityEffect, QStackedWidget,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPalette, QPainter, QPixmap

from services.reporter import Reporter
from ui.theme import _fmt, PALETTE as C, SPACING as S
from ui.components.stat_card import StatCard
from ui.components.bar_chart import ChartContainer
from ui.components.legend import Legend
from ui.components.empty_state import EmptyState
from ui.components.app_icons import asset_pixmap
from data.models import AppStats


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
            pm = QPixmap(pulse_pix)
            from PySide6.QtGui import QPainter as QP, QColor as QC
            p = QP(pm)
            p.setCompositionMode(QP.CompositionMode.CompositionMode_SourceIn)
            p.fillRect(pm.rect(), QC(C.success))
            p.end()
            self._pulse.setPixmap(pm)
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
            pm = QPixmap(pulse_pix)
            from PySide6.QtGui import QPainter as QP, QColor as QC
            p = QP(pm)
            p.setCompositionMode(QP.CompositionMode.CompositionMode_SourceIn)
            p.fillRect(pm.rect(), QC(color))
            p.end()
            self._pulse.setPixmap(pm)
        else:
            self._pulse.setStyleSheet(f"color:{color}; font-size:14px;")

    def update_info(self, info: dict):
        if not info or info.get("paused"):
            self._live_name.setText("Трекинг приостановлен")
            self._live_detail.setText("Нажмите «Возобновить» в меню трея")
            self._live_timer.setText("—")
            self._tint_pulse(C.warning)
            return
        focused = info.get("focused", "")
        display_name = info.get("focused_display", "") or focused
        sec = info.get("focused_sec", 0)
        if focused:
            self._live_name.setText(display_name)
            self._live_detail.setText("Активное окно")
            self._live_timer.setText(_fmt(sec))
            self._tint_pulse(C.success)
        else:
            running = info.get("running_apps", [])
            if running:
                names = ", ".join(
                    a.get("display_name", a["name"]) for a in running[:5])
                self._live_name.setText(f"Запущено: {len(running)}")
                self._live_detail.setText(names)
            else:
                self._live_name.setText("Ожидание…")
                self._live_detail.setText("Нет запущенных отслеживаемых приложений")
            self._live_timer.setText("—")
            self._tint_pulse(C.text_dim)


class DashboardView(QWidget):
    def __init__(self, reporter: Reporter, on_add_app=None, parent=None):
        super().__init__(parent)
        self.reporter = reporter
        self._on_add_app = on_add_app
        self._stats: list[AppStats] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(S.xl, S.xl, S.xl, S.xl)
        root.setSpacing(S.lg)

        self.live_card = LiveCard()
        root.addWidget(self.live_card)

        cards_row = QGridLayout()
        cards_row.setSpacing(S.md)
        self.card_total = StatCard("Всего сегодня", C.accent)
        self.card_active = StatCard("Активное время", C.success)
        self.card_running = StatCard("Запущено сейчас", C.warning)
        self.card_top = StatCard("Топ приложение", C.text)
        for i, card in enumerate(
            [self.card_total, self.card_active, self.card_running, self.card_top]
        ):
            cards_row.addWidget(card, 0, i)
        root.addLayout(cards_row)

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
        root.addLayout(period_row)

        self._chart_container = ChartContainer()
        root.addWidget(self._chart_container)

        self._legend = Legend()
        root.addWidget(self._legend)

        self._content_stack = QStackedWidget()
        self._empty = EmptyState(
            "Нет данных",
            "Запустите отслеживаемое приложение, чтобы увидеть статистику",
            pixmap=asset_pixmap("stats.png", 64),
        )
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["Приложение", "Активное", "Фоновое", "Сессий"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setDefaultSectionSize(32)
        self._table.setSortingEnabled(True)
        self._content_stack.addWidget(self._table)
        self._content_stack.addWidget(self._empty)
        root.addWidget(self._content_stack, 1)

        self.refresh()

    def update_live(self, info: dict):
        self.live_card.update_info(info)

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

    def refresh_live_only(self):
        self._update_cards(self._stats)

    def _update_contents(self, stats):
        self._chart_container.set_stats(stats)
        self._update_cards(stats)
        self._update_table(stats)

    def _update_cards(self, stats):
        total = sum(s.active_seconds + s.background_seconds for s in stats)
        active = sum(s.active_seconds for s in stats)
        self.card_total.set_value(_fmt(total))
        self.card_active.set_value(
            _fmt(active),
            f"{int(active / total * 100) if total else 0}% от общего",
        )
        running = len([s for s in stats if s.active_seconds + s.background_seconds > 0])
        self.card_running.set_value(str(running))
        top = max(
            stats,
            key=lambda s: s.active_seconds + s.background_seconds,
            default=None,
        )
        if top and (top.active_seconds + top.background_seconds) > 0:
            self.card_top.set_value(
                top.display_name or top.process_name,
                _fmt(top.active_seconds + top.background_seconds),
            )

    def _update_table(self, stats):
        if not stats:
            self._content_stack.setCurrentWidget(self._empty)
            return
        self._content_stack.setCurrentWidget(self._table)

        sorting = self._table.isSortingEnabled()
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(stats))
        for i, s in enumerate(stats):
            name = s.display_name or s.process_name
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.ItemDataRole.UserRole, name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 0, name_item)

            for col, val, raw in [
                (1, _fmt(s.active_seconds), s.active_seconds),
                (2, _fmt(s.background_seconds), s.background_seconds),
                (3, str(s.session_count), s.session_count),
            ]:
                item = NumericItem(val)
                item.setData(Qt.ItemDataRole.UserRole, raw)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(i, col, item)
        self._table.setSortingEnabled(sorting)
