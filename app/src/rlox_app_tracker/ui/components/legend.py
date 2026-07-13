from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from rlox_app_tracker.ui.theme import PALETTE as C


class Legend(QWidget):
    def __init__(self):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.addWidget(self._dot(C.accent, "Активное"))
        lay.addWidget(self._dot(C.background_bar, "Фоновое"))
        lay.addStretch()

    def _dot(self, color, text):
        w = QLabel(
            f"<span style='color:{color}'>●</span> "
            f"<span style='color:{C.text_muted}'>{text}</span>"
        )
        w.setStyleSheet("font-size:12px;")
        return w
