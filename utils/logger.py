import logging
import os


def setup_logger(name: str) -> logging.Logger:
    """Set up a logger for the given module or cog name."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers
    if not logger.handlers:
        # Ensure the logs directory exists
        log_path = f"data/logs/{name}.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        # File handler
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # Format: [timestamp] [level] name: message
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger
