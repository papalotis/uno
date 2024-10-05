"""Module to create and configure a logger with a console handler and formatter."""

import logging


def create_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create and configure a logger with a console handler and formatter."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Check if the logger already has handlers to avoid adding multiple
    if not logger.hasHandlers():
        # Create a console handler
        handler = logging.StreamHandler()
        handler.setLevel(level)

        # Create a formatter and set it for the handler
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(handler)

    return logger
