import xml.etree.ElementTree as ET

import addon


def test_commands_in_settings(kodi, session) -> None:
    tree = ET.parse('resources/settings.xml')
    root = tree.getroot()

    commands = set(
        data.text
        for data in root.findall('./section/category/group/setting/data')
        if isinstance(data.text, str)
    )

    # These are the commands existing as string literals in settings
    assert commands == {
        'RunPlugin(plugin://plugin.video.jwb-unofficial/?mode=langlist&set_lang1=1)',
        'RunPlugin(plugin://plugin.video.jwb-unofficial/?mode=langlist&set_lang2=1)',
        'RunPlugin(plugin://plugin.video.jwb-unofficial/?mode=disclaimer)',
    }

    # The langlist will need to call out for language info
    session.add_common_languages()
    # It will require a language to be selected
    kodi.user_choice = 0

    # Test that they all work by calling them with main
    for command in commands:
        query = command.replace('RunPlugin(plugin://plugin.video.jwb-unofficial/', '').rstrip(')')
        kodi.addon_query = query
        addon.main()

    # We should have gotten the theocratic warning on the last one
    assert kodi.dialog_messages == ['STRING #30310']


def test_setting_ids_and_types(kodi):
    tree = ET.parse('resources/settings.xml')
    root = tree.getroot()

    settings = set(
        (setting.get("id"), setting.get("type"))
        for setting in root.findall('./section/category/group/setting')
        if setting.get("type") != "action"
    )

    assert settings == {
        ('enable_fallback', 'boolean'),
        ('jwt_token', 'string'),
        ('lang_history', 'string'),
        ('lang_name', 'string'),
        ('lang_next', 'string'),
        ('language', 'string'),
        ('last_settings_version', 'integer'),
        ('original_audio', 'boolean'),
        ('remember_lang', 'boolean'),
        ('search_tr', 'string'),
        ('second_language', 'string'),
        ('second_language_name', 'string'),
        ('startupmsg', 'boolean'),
        ('subtitle_mode', 'integer'),
        ('subtitles', 'boolean'),
        ('video_res', 'integer'),
        ('video_resolution', 'integer')
    }
