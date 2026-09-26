"""
Classes that represent requests to the plugin itself
"""
from dataclasses import dataclass, asdict, fields
from typing import ClassVar, Dict, TypeVar, Type, Any
from urllib.parse import urlencode

from resources.lib.jwapi import is_convention_release_root
from resources.lib.kodi import kodi

T = TypeVar('T', bound='_Request')


@dataclass
class _Request:
    """Base class for requests to the addon itself"""

    default_values: ClassVar[Dict[str, Any]] = {}
    """Default values for attributes when using from_dict.

    This makes it possible for an argument to be mandatory in internal code, yet optional for requests made
    from Kodi. (The addon may be opened from a bookmark using an older query format, etc).
    """

    mode: ClassVar[str] = ''
    """
    Each Request subclass should override the `mode` class variable with a unique value.
    The `mode` attribute is used by main() to route the request to the correct endpoint.

    Note to self:
        Out of these two API designs, I prefer the first, because it looks cleaner:
        - plugin://plugin/search/?q=word
        - plugin://plugin/?mode=search&q=word

        But that design has two issues:
        - Kodi's `RunAddon` function doesn't seem to accept a path like /search (there are workarounds for this).
        - We need to maintain backwards-compatible watch status, so we'd have to make an exception for the playback
          API endpoint to look like `/?mode=play&media=ThisVideo` anyway.
    """

    @classmethod
    def from_dict(cls: Type[T], user_args: Dict[str, Any]) -> T:
        """Instantiate from a dictionary.

        Ignore unknown arguments, convert to correct types and fill-in some default values.
        """
        valid_name_and_types = {f.name: f.type for f in fields(cls)}

        assert all(type(default_value) is valid_name_and_types[name]
                   for name, default_value in cls.default_values.items())

        filtered_args = {}
        for name, expected_type in valid_name_and_types.items():
            if name not in user_args:
                if name in cls.default_values:
                    filtered_args[name] = cls.default_values[name]
            elif expected_type is str:
                filtered_args[name] = user_args[name]
            elif expected_type is int:
                filtered_args[name] = int(user_args[name])
            elif expected_type is bool:
                filtered_args[name] = bool(int(user_args[name]))
            else:
                raise RuntimeError(f'from_dict() does not support type {expected_type}')

        return cls(**filtered_args)

    @property
    def query(self) -> str:
        """Encoded URL query string"""

        # Exclude fields that are None, False or empty; replace True with '1'
        filtered = {k: 1 if v is True else v
                    for k, v in asdict(self).items()
                    if v is not None
                    if v is not False
                    if v != ''}

        # IMPORTANT: do NOT rename or move 'mode' parameter as that would break watch status for
        # plugin://plugin.video.jwb-unofficial/?mode=play&media=ID

        q = dict(mode=self.mode, **filtered)

        return urlencode(q)

    @property
    def url(self) -> str:
        """Encoded complete URL to the addon itself"""

        # IMPORTANT: URL MUST contain /? to maintain watch status for
        # plugin://plugin.video.jwb-unofficial/?mode=play&media=ID

        return f'plugin://{kodi().get_addon_id()}/?{self.query}'


@dataclass
class BrowseRequest(_Request):
    """Show a category page

    :param category: Category code
    :param hidden: Must be True if the category is inside the convention release category (slower)
    :param media: True if we should use get_category(include_media=True). If this is a middle-category,
                  requesting media is noticeably slower, but if this is an end category, and we don't request
                  media right away, it will result in an extra request. Not a big one, but still unnecessary.
    """
    default_values = {'hidden': False, 'media': False}
    mode = 'browse'

    category: str
    hidden: bool
    media: bool

    def __post_init__(self) -> None:
        if is_convention_release_root(self.category):
            self.hidden = True


@dataclass
class ConfigRequest(_Request):
    """Store a user setting

    :param lang1: Set the main language
    :param lang2: Set the second language
    :param label: Display name for the language
    """
    mode = 'config'

    lang1: str = ''
    lang2: str = ''
    label: str = ''

    def __post_init__(self) -> None:
        assert self.lang1 or self.lang2, 'Invalid request, nothing to do'


@dataclass
class DisclaimerRequest(_Request):
    """Show the disclaimer

    CAREFUL: if you rename this, you must update settings.xml too.
    """
    mode = 'disclaimer'


@dataclass
class LanguageRequest(_Request):
    """Show a list of languages and perform an action when the user selects a language

    :param hidden: Needs to be True if the media or category is a convention release (slower)
    :param play_media: Media code to play in selected language
    :param set_lang1: Set main language
    :param set_lang2: Set second language
    :param shuffle_category: Start playing category in selected language

    CAREFUL: if you rename anything here, you might have to update settings.xml too.
    """
    default_values = {'hidden': False}
    mode = 'langlist'

    hidden: bool
    play_media: str = ''
    set_lang1: bool = False
    set_lang2: bool = False
    shuffle_category: str = ''

    def __post_init__(self):
        assert self.play_media or self.set_lang1 or self.set_lang2 or self.shuffle_category, \
            'Invalid request, nothing to do'


@dataclass
class PlayRequest(_Request):
    """Play a media item

    :param media: Media code
    :param lang: Custom one-time language
    :param no_redirect: Don't redirect to a language agnostic request

    If `lang` is set and `no_redirect` is False, it will redirect to get language agnostic watch status.
    This cannot be done on playlists, as it would interrupt the playback.

    IMPORTANT: do NOT rename 'mode=play' or 'media=' as that would break watch status for
    plugin://plugin.video.jwb-unofficial/?mode=play&media=ID
    """
    default_values = {'hidden': False}
    mode = 'play'

    media: str
    hidden: bool
    lang: str = ''
    no_redirect: bool = False


@dataclass
class SearchRequest(_Request):
    """Open a search box or a search result page

    :param q: Search query (empty = display search box)
    :param audio: Filter for audio clips instead of videos
    :param page: Full URL to a page in the JW search API (used for the Next button)
    """
    mode = 'search'

    q: str = ''
    audio: bool = False
    page: str = ''


@dataclass
class ShuffleRequest(_Request):
    """Start playing random videos from a category

    :param category: Category code
    :param hidden: Must be True if category is inside the convention release category (slower)
    :param lang: Custom language (defaults to language from user settings)
    """
    default_values = {'hidden': False}
    mode = 'playlist'

    category: str
    hidden: bool
    lang: str = ''
