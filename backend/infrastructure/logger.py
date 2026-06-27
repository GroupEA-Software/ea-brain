import logging
import sys
from typing import Optional


_LOGGERS: dict[str, logging.Logger] = {}


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Get or create a structured logger for a module."""
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(f"eabrain.{name}")

    if level is not None:
        logger.setLevel(level)
    else:
        logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        ))
        logger.addHandler(handler)

    _LOGGERS[name] = logger
    return logger


def silence_noisy_loggers() -> None:
    """Mute overly verbose third-party loggers."""
    for name in ("httpx", "urllib3", "openai", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
