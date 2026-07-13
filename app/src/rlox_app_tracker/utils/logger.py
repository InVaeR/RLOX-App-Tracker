import logging
import sys
from logging.handlers import RotatingFileHandler

from rlox_app_tracker.paths import LOG_PATH


def setup_logging():
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    fh = RotatingFileHandler(
        LOG_PATH,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)
