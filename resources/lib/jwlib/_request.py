import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)


def get_json(url: str, query: Optional[dict] = None, *, headers: Optional[dict] = None):
    """Send a query to the server and return loaded JSON"""

    if query is not None:
        # Remove None, convert bool to int
        filtered_query = {
            k: (int(v) if isinstance(v, bool) else v)
            for k, v in query.items()
            if v is not None
        }

        query_string = urllib.parse.urlencode(filtered_query)
        if query_string:
            url += '&' if ('?' in url) else '?'
            url += query_string

    logger.debug(f'opening: {url}')

    r = urllib.request.Request(url, headers=headers or {})
    return json.load(urllib.request.urlopen(r))
