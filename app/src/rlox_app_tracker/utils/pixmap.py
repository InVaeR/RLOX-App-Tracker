from PySide6.QtGui import QPixmap, QPainter, QColor


def tint_pixmap(src: QPixmap, color: str) -> QPixmap:
    pm = QPixmap(src)
    p = QPainter(pm)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    p.fillRect(pm.rect(), QColor(color))
    p.end()
    return pm
