import logging
from typing import Optional

import colorlog


def get_logger(name: str = __name__, level: Optional[int] = None) -> logging.Logger:
    logger = logging.getLogger(name)

    # If no level is provided, it inherits from the parent (the root logger)
    # This allows pytest --log-cli-level=DEBUG to control everything.
    if level:
        logger.setLevel(level)
    elif logger.level == logging.NOTSET:
        logger.setLevel(logging.DEBUG)

    # Add this block to strictly silence noise
    for noisy_logger in [
        "urllib3",
        "requests",
        "charset_normalizer",
        "httpx",
        "httpcore",
        "asyncio",
    ]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
        logging.getLogger(noisy_logger).propagate = False

    # Avoid adding multiple handlers if the logger is reused
    if not logger.handlers:
        handler = colorlog.StreamHandler()

        # Use a simpler format for Pytest to avoid double-formatting
        fmt = "%(log_color)s[%(levelname)s] %(message)s"

        formatter = colorlog.ColoredFormatter(
            fmt,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Prevent logs from bubbling up to the root logger
        # which would cause double-logging in Pytest
        logger.propagate = False

    return logger
