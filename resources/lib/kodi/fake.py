"""
Mock implementation of Kodi interface, for unit testing
"""
import xml.etree.ElementTree as ET
from functools import lru_cache
from typing import List, Union, Dict, TypeVar, Tuple, Sequence, Optional

from resources.lib.kodi.abstract import KodiInterface, ListItem, LogLevel

_T = TypeVar('_T')


@lru_cache
def default_settings() -> List[Tuple[str, str]]:
    """Since this is cached, don't return a dict directly, so it forces a new copy of dict() each time"""

    tree = ET.parse('resources/settings.xml')
    root = tree.getroot()

    return [
        (setting.attrib['id'], default.text or '')
        for setting in root.findall('./section/category/group/setting')
        for default in setting.findall('default')
    ]


class FakeKodiInterface(KodiInterface):
    # Input
    addon_query: str
    system_language: str
    settings: Dict[str, str]
    user_bool: bool
    user_string: str
    user_choice: int
    currently_playing_file: Optional[str] = None
    fake_build_version: str = "21.3 (21.3.0) Git:20260916-nogitfound"

    # Output
    screen_items: List[ListItem]
    resolved: ListItem
    subtitle_visibility: bool
    started_playlist: List[ListItem]

    def __init__(self):
        self.settings = dict(default_settings())
        self.notifications = []
        self.dialog_messages = []
        self.executed_commands = []
        self.logged_messages: List[Tuple[LogLevel, str]] = []

    #
    # Addon info
    #

    def get_addon_fanart(self) -> str:
        return 'FANART_PATH'

    def get_addon_id(self) -> str:
        return 'plugin.video.jwb-unofficial'

    def get_addon_name(self) -> str:
        return 'ADDON_NAME'

    def get_addon_path(self) -> str:
        return 'ADDON_PATH'

    def get_addon_profile_dir(self) -> str:
        return 'ADDON_PROFILE_DIRECTORY'

    def get_addon_query(self) -> str:
        return self.addon_query

    def get_localized_string(self, id: int) -> str:
        return f'STRING #{id}'

    def get_setting(self, key: str) -> str:
        return self.settings[key]

    def get_setting_bool(self, key: str) -> bool:
        return self.get_setting(key) == 'true'

    def set_setting(self, key: str, value: str) -> None:
        assert key in self.settings
        self.settings[key] = value

    def set_setting_bool(self, key: str, value: bool) -> None:
        self.set_setting(key, 'true' if value else 'false')

    #
    # Directory plugin
    #

    @property
    def handle(self) -> int:
        return 0

    def add_items(self, items: Sequence[ListItem]) -> None:
        self.screen_items = list(items)

    def set_resolved_url(self, item: ListItem):
        self.resolved = item
        self.currently_playing_file = item.url

    #
    # GUI elements
    #

    def notify(self, heading: str, message: str) -> None:
        self.notifications.append(f'{heading}: {message}')

    def input_dialog(self) -> str:
        return self.user_string

    def ok_dialog(self, title: str, message: str) -> bool:
        self.dialog_messages.append(f'{title}: {message}')
        return True

    def question_dialog(self, title: str, message: str) -> bool:
        return self.user_bool

    def selection_dialog(self, title: str, items: Sequence[Union[str, ListItem]]) -> int:
        return self.user_choice

    def text_dialog(self, title: str, message: str) -> None:
        self.dialog_messages.append(f'{title}: {message}')

    #
    # Internals
    #

    def get_build_version(self) -> str:
        return self.fake_build_version

    def get_system_language(self) -> str:
        return self.system_language

    def execute(self, command: str) -> None:
        self.executed_commands.append(command)

    def log(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        self.logged_messages.append((level, message))

    #
    # Player
    #

    def get_playing_file(self) -> str:
        if self.currently_playing_file is None:
            raise Exception('No playing file')
        return self.currently_playing_file

    def show_subtitles(self, show: bool) -> None:
        self.subtitle_visibility = show

    def start_playlist(self, items: Sequence[ListItem]):
        self.started_playlist = list(items)
