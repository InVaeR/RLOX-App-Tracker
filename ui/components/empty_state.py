from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from ui.theme import PALETTE as C


class EmptyState(QWidget):
    def __init__(self, title: str, subtitle: str,
                 button_text: str = "", on_click=None,
                 pixmap: QPixmap = None, emoji: str = ""):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(12)

        ic = QLabel()
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if pixmap and not pixmap.isNull():
            ic.setPixmap(pixmap)
        elif emoji:
            ic.setText(emoji)
            ic.setStyleSheet("font-size:52px;")
        lay.addWidget(ic)

        t = QLabel(title)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(f"font-size:17px; font-weight:600; color:{C.text};")

        s = QLabel(subtitle)
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.setStyleSheet(f"font-size:13px; color:{C.text_muted};")

        lay.addWidget(t)
        lay.addWidget(s)

        if button_text and on_click:
            btn = QPushButton(button_text)
            btn.setObjectName("primary")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(on_click)
            lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
