# Licensed under the Apache License, Version 2.0

from resources.lib.compat import migrate_settings
from resources.lib.endpoints import *
from resources.lib.jwgui import show_disclaimer
from resources.lib.jwlib.media import NotFoundError
from resources.lib.kodi import kodi
from resources.lib.log import configure_logging, notify_and_log_traceback
from resources.lib.requests import *
from resources.lib.translations import *


def main() -> None:
    configure_logging()

    try:
        migrate_settings()
    except Exception:
        notify_and_log_traceback("Failed to perform settings migration")

    args = kodi().get_addon_args()
    mode = args.get('mode', '')

    # hidden= is a required argument on some requests, but it is filtered out if false,
    # so we just lazily add it back to avoid Pydantic errors (superfluos arguments will
    # be ignored anyway).
    args.setdefault('hidden', '0')

    try:
        if mode == BrowseRequest.mode:
            browse_endpoint(BrowseRequest.from_dict(args))
        elif mode == ConfigRequest.mode:
            config_endpoint(ConfigRequest.from_dict(args))
        elif mode == DisclaimerRequest.mode:
            show_disclaimer()
        elif mode == LanguageRequest.mode:
            langlist_endpoint(LanguageRequest.from_dict(args))
        elif mode == PlayRequest.mode:
            play_endpoint(PlayRequest.from_dict(args))
        elif mode == SearchRequest.mode:
            search_endpoint(SearchRequest.from_dict(args))
        elif mode == ShuffleRequest.mode:
            shuffle_endpoint(ShuffleRequest.from_dict(args))
        else:
            home_endpoint()

    except NotFoundError:
        notify_and_log_traceback(tr(Not_available_in_selected_language))

    except OSError:
        # Assume all OSErrors are just a bad connection and exit nicely
        notify_and_log_traceback(tr(Connection_error))


if __name__ == '__main__':
    main()
