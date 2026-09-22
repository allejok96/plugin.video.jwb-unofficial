from resources.lib.requests import ConfigRequest
from resources.lib.settings import settings

__all__ = (
    'config_endpoint',
)


def config_endpoint(request: ConfigRequest):
    """API endpoint that stores a settings value"""

    if request.lang1:
        settings.set_language(request.lang1, request.label)
    elif request.lang2:
        settings.set_second_language(request.lang2, request.label)
