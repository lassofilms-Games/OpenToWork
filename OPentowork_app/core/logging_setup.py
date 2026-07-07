import logging
from logging.handlers import RotatingFileHandler

from core.config_store import LOGS_DIR

LOG_FILE = LOGS_DIR / "opentowork_app.log"


def setup_logging():
    logger = logging.getLogger("OPentowork_app")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
    return logger
