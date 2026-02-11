"""Loguru logging configuration.

Call setup_logging() once at application startup to configure sinks.
All other modules simply do `from loguru import logger` and log normally.
"""

import sys
from pathlib import Path

from loguru import logger

# Log directory at project root
LOG_DIR = Path(__file__).resolve().parents[3] / "logs"


def setup_logging(level: str = "DEBUG") -> None:
    """Configure loguru with stderr and rotating file sinks.

    Args:
        level: Minimum log level (default DEBUG).
    """
    # Remove the default stderr handler so we can reconfigure it
    logger.remove()

    # Sink 1: stderr — human-readable, colored
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )

    # Sink 2: rotating log file — rotate every 3 hours, delete after 1 day
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        LOG_DIR / "orchestrator.log",
        level=level,
        rotation="3 hours",
        retention="1 day",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )
