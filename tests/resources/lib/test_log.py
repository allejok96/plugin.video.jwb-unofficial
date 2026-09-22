import logging

from resources.lib.kodi import LogLevel
from resources.lib.log import _KodiLogForwarder, configure_logging


def make_record(level: int, message: str, name: str = 'resources.lib.jwapi') -> logging.LogRecord:
    return logging.LogRecord(
        name=name, level=level, pathname=__file__, lineno=1,
        msg=message, args=(), exc_info=None,
    )


def test_emit_forwards_formatted_message_and_level(kodi):
    _KodiLogForwarder().emit(make_record(logging.WARNING, 'something went wrong'))

    assert kodi.logged_messages == [(LogLevel.WARN, 'resources.lib.jwapi: something went wrong')]


def test_emit_defaults_unknown_level_to_info(kodi):
    _KodiLogForwarder().emit(make_record(15, 'custom level'))

    assert kodi.logged_messages == [(LogLevel.INFO, 'resources.lib.jwapi: custom level')]


def test_configure_logging_installs_kodi_handler_at_debug_level(monkeypatch):
    captured = {}

    def fake_basic_config(*, handlers, level):
        captured['handlers'] = handlers
        captured['level'] = level

    monkeypatch.setattr(logging, 'basicConfig', fake_basic_config)

    configure_logging()

    assert captured['level'] == logging.DEBUG
    assert len(captured['handlers']) == 1
    assert isinstance(captured['handlers'][0], _KodiLogForwarder)
