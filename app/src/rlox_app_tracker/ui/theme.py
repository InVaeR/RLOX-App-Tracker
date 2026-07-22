from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    bg = "#112c25"
    surface = "#183630"
    surface_hover = "#1f4039"
    sidebar = "#0d221c"
    border = "#2a5d4a"
    text = "#e5f5f0"
    text_muted = "#a7c9bc"
    text_dim = "#7ba89a"
    accent = "#14fab1"
    accent_hover = "#4fffc6"
    accent_soft = "#1a4d3e"
    success = "#14fab1"
    warning = "#f5a623"
    danger = "#f0616d"
    background_bar = "#1f4039"


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
