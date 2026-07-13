from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from rlox_app_tracker.ui.theme import PALETTE as C


class AppItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(0, 54)

    def paint(self, painter, option, index):
        painter.save()
        rect = option.rect

        if option.state & QStyle.StateFlag.State_Selected:
            painter.setBrush(QColor(C.accent_soft))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect.adjusted(4, 2, -4, -2), 8, 8)
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.setBrush(QColor(C.surface_hover))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect.adjusted(4, 2, -4, -2), 8, 8)

        icon = index.data(Qt.ItemDataRole.DecorationRole)
        icon_size = 28
        icon_x = rect.left() + 14
        icon_y = rect.top() + (rect.height() - icon_size) // 2
        if icon:
            icon.paint(painter, QRect(icon_x, icon_y, icon_size, icon_size))

        text_x = icon_x + icon_size + 12
        text_w = rect.right() - text_x - 12

        name = index.data(Qt.ItemDataRole.DisplayRole) or ""
        exe = index.data(Qt.ItemDataRole.UserRole) or ""

        painter.setPen(QColor(C.text))
        f = QFont(painter.font())
        f.setPointSize(10)
        f.setBold(True)
        painter.setFont(f)
        fm = painter.fontMetrics()
        name_el = fm.elidedText(name, Qt.TextElideMode.ElideRight, text_w)
        painter.drawText(text_x, rect.top() + 12, text_w, 18,
                         Qt.AlignmentFlag.AlignVCenter, name_el)

        painter.setPen(QColor(C.text_dim))
        f2 = QFont(painter.font())
        f2.setPointSize(8)
        f2.setBold(False)
        painter.setFont(f2)
        fm2 = painter.fontMetrics()
        exe_el = fm2.elidedText(exe, Qt.TextElideMode.ElideMiddle, text_w)
        painter.drawText(text_x, rect.top() + 30, text_w, 16,
                         Qt.AlignmentFlag.AlignVCenter, exe_el)

        painter.restore()
