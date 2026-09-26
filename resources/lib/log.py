"""
Adapter between Python logging and Kodi logging
"""

import logging
import traceback

from resources.lib.kodi import kodi, LogLevel


class _KodiLogForwarder(logging.Handler):
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
        self.setFormatter(logging.Formatter(f'{kodi().get_addon_id()}.%(name)s: %(message)s'))

    def emit(self, record: logging.LogRecord):
        level = self.LEVELS.get(record.levelno, LogLevel.INFO)
        kodi().log(self.format(record), level)


def configure_logging():
    logging.basicConfig(handlers=[_KodiLogForwarder()], level=logging.DEBUG)


def notify_and_log_traceback(heading: str, message: str):
    kodi().notify(heading, message)
    kodi().log(message, LogLevel.ERROR)
    kodi().log(traceback.format_exc(), LogLevel.ERROR)
