"""
Kodi interface, all calls to Kodi should go through this

This makes it easier to do version-specific stuff and unit testing.
"""

from abc import abstractmethod, ABC
from dataclasses import field, dataclass
from enum import Enum, auto
from typing import List, Tuple, Dict, final, Union, Sequence, Optional
from urllib.parse import parse_qs

__all__ = (
    'ItemType',
    'ListItem',
    'LogLevel',
    'KodiInterface',
)


class LogLevel(Enum):
    DEBUG = auto()
    INFO = auto()
    WARN = auto()
    ERROR = auto()
    FATAL = auto()


class ItemType(Enum):
    FOLDER = 'folder'
    AUDIO = 'music'
    OTHER = 'other'
    VIDEO = 'video'


@dataclass
class ListItem:
    """Basically same as Kodi ListItem but may be a bit faster

    For some reason the setters of Kodi have been slow in the past...
    Maybe they are updating the UI dynamically? Idk. Anyway this is more decoupled.
    """
    title: str
    url: str
    type: ItemType
    date: str = ''  # YYYY-MM-DD
    description: str = ''
    duration: int = 0
    fanart: str = ''
    icon: Optional[str] = None
    menu: List[Tuple[str, str]] = field(default_factory=list)  # [(title, url), ...]
    subtitles: List[str] = field(default_factory=list)


class KodiInterface(ABC):
    @final
    def get_addon_args(self) -> Dict[str, str]:
        """Return the addon's URL query as a dict"""
        return {k: v[0] for k, v in parse_qs(self.get_addon_query().lstrip('?')).items()}

    @final
    def get_setting_bool(self, key: str) -> bool:
        """TODO Kodi 20 use xbmcaddon.Addon(id).getSettings().getBool(id)"""
        return self.get_setting(key) == 'true'

    @final
    def set_setting_bool(self, key: str, value: bool) -> None:
        self.set_setting(key, 'true' if value else 'false')

    #
    # Addon info
    #

    @abstractmethod
    def get_addon_fanart(self) -> str:
        ...

    @abstractmethod
    def get_addon_id(self) -> str:
        ...

    @abstractmethod
    def get_addon_name(self) -> str:
        ...

    @abstractmethod
    def get_addon_path(self) -> str:
        ...

    @abstractmethod
    def get_addon_profile_dir(self) -> str:
        ...

    @abstractmethod
    def get_addon_query(self) -> str:
        ...

    @abstractmethod
    def get_localized_string(self, id: int) -> str:
        ...

    @abstractmethod
    def get_setting(self, key: str) -> str:
        ...

    @abstractmethod
    def set_setting(self, key: str, value: str) -> None:
        ...

    #
    # Directory plugin
    #

    @property
    @abstractmethod
    def handle(self) -> int:
        ...

    @abstractmethod
    def add_items(self, items: Sequence[ListItem]) -> None:
        """Call once with all items that should be on screen"""
        ...

    @abstractmethod
    def set_resolved_url(self, item: ListItem) -> None:
        ...

    #
    # GUI elements
    #

    @abstractmethod
    def notify(self, message: str) -> None:
        ...

    @abstractmethod
    def input_dialog(self) -> str:
        ...

    @abstractmethod
    def question_dialog(self, title: str, message: str) -> bool:
        ...

    @abstractmethod
    def selection_dialog(self, title: str, items: Sequence[Union[str, ListItem]]) -> int:
        ...

    @abstractmethod
    def text_dialog(self, title: str, message: str) -> None:
        ...

    #
    # Internals
    #

    @abstractmethod
    def get_system_language(self) -> str:
        ...

    @abstractmethod
    def execute(self, command: str) -> None:
        ...

    @abstractmethod
    def log(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        ...

    #
    # Player
    #

    @abstractmethod
    def get_subtitles(self) -> List[str]:
        ...

    @abstractmethod
    def show_subtitles(self, show: bool) -> None:
        ...

    @abstractmethod
    def start_playlist(self, items: Sequence[ListItem]) -> None:
        ...
