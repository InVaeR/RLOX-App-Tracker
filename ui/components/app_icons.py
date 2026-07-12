import os
from PySide6.QtWidgets import QFileIconProvider
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QFileInfo
from config import APP_DIR

_provider = QFileIconProvider()
_cache: dict[str, QIcon] = {}

_ICONS_DIR = APP_DIR / "assets" / "images" / "icons"
_asset_cache: dict[str, QIcon] = {}


def get_app_icon(exe_path: str | None) -> QIcon | None:
    if not exe_path:
        return None
    if exe_path in _cache:
        return _cache[exe_path]
    if os.path.exists(exe_path):
        icon = _provider.icon(QFileInfo(exe_path))
        _cache[exe_path] = icon
        return icon
    return None


def asset_icon(name: str) -> QIcon:
    if name in _asset_cache:
        return _asset_cache[name]
    p = _ICONS_DIR / name
    if p.exists():
        icon = QIcon(str(p))
        _asset_cache[name] = icon
        return icon
    return QIcon()


def asset_pixmap(name: str, size: int = 48) -> QPixmap:
    icon = asset_icon(name)
    if not icon.isNull():
        return icon.pixmap(size, size)
    return QPixmap()
