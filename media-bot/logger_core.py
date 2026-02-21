# -*- coding: utf-8 -*-

import logging
import sys
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "system.log")

# =============================
# CONFIGURE ROOT LOGGER
# =============================
logger = logging.getLogger("MEDIA_SYSTEM")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

# Console (Docker logs)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# Rotating file log
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,
    backupCount=5
)
file_handler.setFormatter(formatter)

# Avoid duplicate handlers
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


# =============================
# SIMPLE LOG FUNCTION
# =============================
def log(tag, level, message):
    """
    tag: TOOL1 / WORKER / TOOL5 / MASTER
    level: INFO / WARNING / ERROR
    message: string
    """
    full_msg = f"{tag} | {message}"

    level = level.upper()

    if level == "INFO":
        logger.info(full_msg)
    elif level == "WARNING":
        logger.warning(full_msg)
    elif level == "ERROR":
        logger.error(full_msg)
    else:
        logger.info(full_msg)
