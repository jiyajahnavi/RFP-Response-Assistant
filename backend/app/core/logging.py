import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure centralized application logger."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    logger = logging.getLogger("rfp_assistant")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger
