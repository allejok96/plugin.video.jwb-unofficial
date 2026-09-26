from ._api_responses import LanguageDict
from ._language import Language


def create_language(d: LanguageDict) -> Language:
    return Language(
        code=d['code'],
        iso=d.get('locale', ''),
        name=d.get('name', ''),
        rtl=d.get('isRTL', False),
        script=d.get('script', ''),
        signed=d.get('isSignLanguage', False),
        vernacular=d.get('vernacular', ''),
    )
