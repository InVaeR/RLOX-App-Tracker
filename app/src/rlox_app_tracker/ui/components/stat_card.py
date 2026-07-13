from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from rlox_app_tracker.ui.theme import PALETTE as C, SPACING as S


class StatCard(QFrame):
    def __init__(self, title: str, accent: str = C.accent):
        super().__init__()
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(S.lg, S.md, S.lg, S.md)
        lay.setSpacing(S.xs)

        self._title = QLabel(title)
        self._title.setStyleSheet(
            f"color:{C.text_muted}; font-size:12px; font-weight:600;"
        )

        self._value = QLabel("—")
        self._value.setStyleSheet(f"color:{accent}; font-size:28px; font-weight:700;")

        self._sub = QLabel("")
        self._sub.setStyleSheet(f"color:{C.text_dim}; font-size:12px;")

        lay.addWidget(self._title)
        lay.addWidget(self._value)
        lay.addWidget(self._sub)

    def set_value(self, value: str, sub: str = ""):
        self._value.setText(value)
        self._sub.setText(sub)

    def set_title(self, title: str):
        self._title.setText(title)
