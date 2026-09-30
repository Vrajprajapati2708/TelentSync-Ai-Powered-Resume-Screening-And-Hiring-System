# ============================================================
#  TalentSync — Application Logger
#  Centralised logging for all modules.
# ============================================================

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger for the given module name.
    Logs to stdout with a consistent format.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)-8s %(name)s — %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger
