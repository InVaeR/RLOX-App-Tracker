from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    bg = "#244e3f"  # pine-teal
    surface = "#315a4e"  # pine-teal-2
    surface_hover = "#405e52"  # granite
    sidebar = "#1a3a2f"  # darker pine-teal
    border = "#4a6e5e"  # mid tone
    text = "#cae6d8"  # honeydew
    text_muted = "#a5c5b9"  # ash-grey
    text_dim = "#8aad9e"  # darker ash-grey
    accent = "#cae6d8"  # honeydew
    accent_hover = "#daf0e2"  # lighter honeydew
    accent_soft = "#2a5d4a"  # semi-transparent accent
    success = "#3ecf8e"
    warning = "#f5a623"
    danger = "#f0616d"
    background_bar = "#405e52"  # granite


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
