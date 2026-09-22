import logging

from resources.lib.endpoints import home
from resources.lib.jwlib.media import Category
from resources.lib.jwlib.media.const import ROOT_CATEGORY, TAG_EXCLUDE_APPLETV
from resources.lib.settings import settings


def test_first_time_setup_configures_language_and_shows_disclaimer(kodi, session):
    session.add_common_languages()
    kodi.system_language = 'sv'

    home.first_time_setup()

    assert settings.language == 'Z'
    assert settings.first_run is False
    assert kodi.dialog_messages

    kodi.dialog_messages.clear()
    home.first_time_setup()

    assert not kodi.dialog_messages


def test_get_root_categories(kodi, sessions):
    session = sessions.add('E', hidden=True)
    session.categories[ROOT_CATEGORY] = Category.create(
        key=ROOT_CATEGORY,
        session=session,
        type='container',
        subcategories=['Visible', 'Hidden'],
    )
    session.categories['Visible'] = Category.create(
        key='Visible',
        session=session,
        type='ondemand',
    )
    session.categories['Hidden'] = Category.create(
        key='Hidden',
        session=session,
        type='ondemand',
        tags=[TAG_EXCLUDE_APPLETV],
    )

    result = home.get_root_categories()

    assert [cat.key for cat in result] == ['Visible']


def test_set_addon_lang_from_system_lang(languages):
    assert settings.language == 'E'

    home.set_addon_lang_from_system_lang('sv', languages)

    assert settings.language == 'Z'


def test_set_addon_lang_from_system_lang_no_match(kodi, languages, caplog):
    with caplog.at_level(logging.DEBUG):
        home.set_addon_lang_from_system_lang('xx', languages)

    assert settings.language == 'E'
    assert ('resources.lib.endpoints.home', logging.ERROR, "Failed to auto configure language to 'xx'") \
           in caplog.record_tuples


def test_get_fanart_path():
    assert home.get_fanart_path() == 'ADDON_PATH/FANART_PATH'


def test_home_endpoint(kodi, sessions):
    kodi.system_language = 'en'

    # This session is used by the language list
    lang_session = sessions.add('E')
    lang_session.add_common_languages()

    # This session is used by category list
    cat_session = sessions.add('E', hidden=True)

    cat_session.categories[ROOT_CATEGORY] = Category.create(
        key=ROOT_CATEGORY,
        name='Root',
        session=cat_session,
        type='container',
        subcategories=['sub'],
    )
    cat_session.categories['sub'] = Category.create(
        key='sub',
        name='Subcategory',
        session=cat_session,
        type='ondemand',
    )

    home.home_endpoint()

    assert [i.title for i in kodi.screen_items] == ['Subcategory', 'Search']
