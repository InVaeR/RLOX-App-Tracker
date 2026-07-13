def fmt_duration(seconds: int, short: bool = False) -> str:
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    if short:
        return f"{h} ч {m} мин" if h else f"{m} мин"
    if h:
        return f"{h} ч {m} мин"
    if m:
        return f"{m} мин {s} сек"
    return f"{s} сек"
