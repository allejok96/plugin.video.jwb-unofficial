"""
Adapter between Python logging and Kodi logging
"""

import logging
import traceback

from resources.lib.kodi import kodi, LogLevel

__all__ = (
    'configure_logging',
    'notify_and_log_traceback',
)


class KodiLogForwarder(logging.Handler):
    """Log handler that passes Python's logging messages to the Kodi logger"""

    LEVELS = {
        logging.DEBUG: LogLevel.DEBUG,
        logging.INFO: LogLevel.INFO,
        logging.WARNING: LogLevel.WARN,
        logging.ERROR: LogLevel.ERROR,
        logging.FATAL: LogLevel.FATAL,
    }

    def __init__(self):
        super().__init__()
        self.setFormatter(logging.Formatter('%(name)s: %(message)s'))

    def emit(self, record: logging.LogRecord):
        level = self.LEVELS.get(record.levelno, LogLevel.INFO)
        kodi().log(self.format(record), level)


def configure_logging():
    logging.basicConfig(handlers=[KodiLogForwarder()], level=logging.DEBUG)


def notify_and_log_traceback(message: str):
    kodi().notify(message)
    kodi().log(message, LogLevel.ERROR)
    kodi().log(traceback.format_exc(), LogLevel.ERROR)
