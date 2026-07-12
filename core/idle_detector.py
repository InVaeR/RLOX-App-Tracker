from ctypes import Structure, windll, c_uint, sizeof, byref


class LASTINPUTINFO(Structure):
    _fields_ = [("cbSize", c_uint), ("dwTime", c_uint)]


def get_idle_seconds() -> float:
    info = LASTINPUTINFO()
    info.cbSize = sizeof(info)
    if not windll.user32.GetLastInputInfo(byref(info)):
        return 0.0
    millis = windll.kernel32.GetTickCount() - info.dwTime
    return millis / 1000.0
