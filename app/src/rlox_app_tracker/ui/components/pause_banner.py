from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from rlox_app_tracker.ui.theme import PALETTE as C


class PauseBanner(QFrame):
    resume_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {C.warning};
                border-radius: 0;
            }}
            QLabel {{ color: {C.text}; font-weight: 600; font-size: 13px; }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.addWidget(QLabel("Отслеживание приостановлено"))
        lay.addStretch()
        btn = QPushButton("Возобновить")
        btn.setStyleSheet(
            f"background:{C.text}; color:{C.surface}; border:none; "
            "border-radius:6px; padding:6px 14px;"
        )
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.resume_clicked.emit)
        lay.addWidget(btn)
        self.hide()
