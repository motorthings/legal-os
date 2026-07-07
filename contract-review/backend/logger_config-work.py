"""
Centralized logging configuration for the application.
Replaces print() statements with proper Python logging.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logging(log_level=None):
    """
    Set up application-wide logging configuration.

    Args:
        log_level: Override log level (defaults to environment variable or INFO)
    """
    # Determine log level from environment or parameter
    if log_level is None:
        log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)

    # Create logger
    logger = logging.getLogger('contractreview')
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Format: timestamp - level - module - message
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # Optional file handler (only if LOG_FILE is set)
    log_file = os.getenv('LOG_FILE')
    if log_file:
        # Ensure log directory exists (especially for volume-mounted paths)
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except OSError as e:
                print(f"⚠️  Could not create log directory {log_dir}: {e}")
                # Fall back to console-only logging
                return logger

        try:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError as e:
            print(f"⚠️  Could not create log file {log_file}: {e}")
            # Continue with console-only logging

    return logger

def get_logger(name: str = None):
    """
    Get a logger instance for a specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f'contractreview.{name}')
    return logging.getLogger('contractreview')
