from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    bg = "#0f1117"
    surface = "#171a21"
    surface_hover = "#1e222b"
    sidebar = "#13151c"
    border = "#252a35"
    text = "#e4e7ec"
    text_muted = "#8b909a"
    text_dim = "#5c616b"
    accent = "#5b8def"
    accent_hover = "#6f9bf2"
    accent_soft = "#1d2740"
    success = "#3ecf8e"
    warning = "#f5a623"
    danger = "#f0616d"
    background_bar = "#3a4150"


@dataclass(frozen=True)
class Spacing:
    xs = 4
    sm = 8
    md = 12
    lg = 16
    xl = 24
    xxl = 32


@dataclass(frozen=True)
class Radius:
    sm = 6
    md = 10
    lg = 14
    pill = 999


PALETTE = Palette()
SPACING = Spacing()
RADIUS = Radius()
FONT_FAMILY = "Segoe UI"


def _fmt(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h} ч {m} мин"
    if m:
        return f"{m} мин {s} сек"
    return f"{s} сек"

