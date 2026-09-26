# Licensed under the Apache License, Version 2.0

from resources.lib.jwlib.media import NotFoundError

from resources.lib.migrate import migrate_settings
from resources.lib.endpoints.browse import browse_endpoint
from resources.lib.endpoints.config import config_endpoint
from resources.lib.endpoints.home import home_endpoint
from resources.lib.endpoints.langlist import langlist_endpoint
from resources.lib.endpoints.play import play_endpoint
from resources.lib.endpoints.search import search_endpoint
from resources.lib.endpoints.shuffle import shuffle_endpoint
from resources.lib.jwgui import show_disclaimer
from resources.lib.kodi import kodi
from resources.lib.log import configure_logging, notify_and_log_traceback
from resources.lib.requests import (BrowseRequest, ConfigRequest, DisclaimerRequest,
                                    LanguageRequest, PlayRequest, SearchRequest, ShuffleRequest)
from resources.lib.translations import *


def main() -> None:
    configure_logging()

    if not migrate_settings():
        kodi().notify(tr(Settings_migration_error), tr(See_the_log))

    args = kodi().get_addon_args()
    mode = args.get('mode', '')

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
        notify_and_log_traceback(tr(Not_available_in_selected_language), '')

    except OSError:
        # Assume all OSErrors are just a bad connection and exit nicely
        notify_and_log_traceback(tr(Connection_error), tr(See_the_log))


if __name__ == '__main__':
    main()
