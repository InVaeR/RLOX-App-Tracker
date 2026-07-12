from ui.theme import PALETTE as C, RADIUS as R

APP_QSS = f"""
* {{
    font-family: 'Segoe UI', sans-serif;
    color: {C.text};
    outline: none;
}}

QMainWindow, QWidget#root {{
    background-color: {C.bg};
}}

QWidget#sidebar {{
    background-color: {C.sidebar};
    border-right: 1px solid {C.border};
}}

QPushButton#navItem {{
    background: transparent;
    border: none;
    border-radius: {R.md}px;
    padding: 10px 14px;
    text-align: left;
    font-size: 14px;
    color: {C.text_muted};
}}
QPushButton#navItem:hover {{
    background-color: {C.surface_hover};
    color: {C.text};
}}
QPushButton#navItem:checked {{
    background-color: {C.accent_soft};
    color: {C.text};
    font-weight: 600;
}}

QFrame#card {{
    background-color: {C.surface};
    border: 1px solid {C.border};
    border-radius: {R.lg}px;
}}

QTableWidget {{
    background-color: transparent;
    border: none;
    gridline-color: transparent;
    selection-background-color: {C.accent_soft};
    selection-color: {C.text};
}}
QTableWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {C.border};
    background-color: transparent;
    color: {C.text};
}}
QTableWidget::item:hover {{
    background-color: {C.surface_hover};
}}
QHeaderView {{
    background-color: transparent;
}}
QHeaderView::section {{
    background-color: transparent;
    border: none;
    border-bottom: 1px solid {C.border};
    padding: 8px 12px;
    color: {C.text_muted};
    font-size: 12px;
    font-weight: 600;
}}
QTableCornerButton::section {{ background-color: transparent; border: none; }}

QPushButton {{
    background-color: {C.surface};
    border: 1px solid {C.border};
    border-radius: {R.md}px;
    padding: 9px 18px;
    font-size: 13px;
    color: {C.text};
}}
QPushButton:hover {{
    background-color: {C.surface_hover};
    border-color: {C.accent};
}}
QPushButton#primary {{
    background-color: {C.accent};
    border: none;
    color: white;
    font-weight: 600;
}}
QPushButton#primary:hover {{ background-color: {C.accent_hover}; }}
QPushButton#danger {{
    background-color: transparent;
    border: 1px solid {C.danger};
    color: {C.danger};
}}
QPushButton#danger:hover {{ background-color: {C.danger}; color: white; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {C.bg};
    border: 1px solid {C.border};
    border-radius: {R.md}px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {C.accent};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {C.accent};
}}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    background-color: {C.surface};
    border: 1px solid {C.border};
    border-radius: {R.md}px;
    selection-background-color: {C.accent_soft};
    padding: 4px;
}}

QCheckBox {{ spacing: 8px; font-size: 13px; }}
QCheckBox::indicator {{
    width: 20px; height: 20px;
    border-radius: {R.sm}px;
    border: 1px solid {C.border};
    background: {C.bg};
}}
QCheckBox::indicator:checked {{
    background-color: {C.accent};
    border-color: {C.accent};
}}

QGroupBox {{
    border: 1px solid {C.border};
    border-radius: {R.md}px;
    margin-top: 12px;
    padding: 18px 16px 12px 16px;
    font-weight: 600;
    font-size: 13px;
    color: {C.text_muted};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
}}

QStackedWidget, QScrollArea {{ background: transparent; }}

QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C.border}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {C.text_dim}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

QStatusBar {{
    background-color: {C.sidebar};
    border-top: 1px solid {C.border};
    color: {C.text_muted};
    font-size: 12px;
}}

QListWidget {{
    background-color: {C.bg};
    border: 1px solid {C.border};
    border-radius: {R.md}px;
}}
QListWidget::item {{
    padding: 4px 8px;
}}
"""
