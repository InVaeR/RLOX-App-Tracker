from PySide6.QtWidgets import QStackedWidget, QGraphicsOpacityEffect
from PySide6.QtCore import QPropertyAnimation, QEasingCurve


class FadeStack(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._anim = None

    def setCurrentIndex(self, index):
        if index == self.currentIndex():
            return
        if self._anim:
            self._anim.stop()
            self._anim.deleteLater()
            self._anim = None
        prev = self.currentWidget()
        if prev:
            prev.setGraphicsEffect(None)
        super().setCurrentIndex(index)
        w = self.currentWidget()
        eff = QGraphicsOpacityEffect(w)
        w.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(180)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: w.setGraphicsEffect(None))
        anim.start()
        self._anim = anim
