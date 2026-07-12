from datetime import date

__version_base__ = "1.0.0"
__date_stamp__ = date.today().strftime("%Y%m%d")
__version__ = f"{__version_base__}-{__date_stamp__}"
__app_name__ = "RusLOXPy"
__author__ = "RusLOX"
UPDATE_URL = "https://api.github.com/repos/InVaeR/RusLOXPy/releases/latest"


def build_number() -> int:
    return int(__date_stamp__[4:])
