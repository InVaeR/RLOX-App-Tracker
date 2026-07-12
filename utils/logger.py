import logging
import sys

from config import DATA_DIR


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(DATA_DIR / "app.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
