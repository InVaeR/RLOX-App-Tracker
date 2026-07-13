from ctypes import Structure, byref, c_uint, sizeof, windll

UINT32_MASK = 0xFFFFFFFF


class LASTINPUTINFO(Structure):
    _fields_ = [
        ("cbSize", c_uint),
        ("dwTime", c_uint),
    ]


def get_idle_seconds() -> float:
    info = LASTINPUTINFO(cbSize=sizeof(LASTINPUTINFO))

    if not windll.user32.GetLastInputInfo(byref(info)):
        return 0.0

    current = windll.kernel32.GetTickCount64() & UINT32_MASK
    elapsed_ms = (current - info.dwTime) & UINT32_MASK
    return elapsed_ms / 1000.0
