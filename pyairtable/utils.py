from datetime import datetime, date
from typing import Union

from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from pyairtable import __version__ as pyairtable_version


def datetime_to_iso_str(value: datetime) -> str:
    """
    Converts ``datetime`` object into Airtable compatible ISO 8601 string
    e.g. "2014-09-05T12:34:56.000Z"

    Args:
        value: datetime object
    """
    return value.isoformat(timespec="milliseconds") + "Z"


def datetime_from_iso_str(value: str) -> datetime:
    """
    Converts ISO 8601 datetime string into a ``datetime`` object.
    Expected format is "2014-09-05T07:00:00.000Z"

    Args:
        value: datetime string e.g. "2014-09-05T07:00:00.000Z"
    """
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")


def date_to_iso_str(value: Union[date, datetime]) -> str:
    """
    Converts ``date`` or ``datetime`` object into Airtable compatible ISO 8601 string
    e.g. "2014-09-05"

    Args:
        value: date or datetime object
    """
    return value.strftime("%Y-%m-%d")


def date_from_iso_str(value: str) -> date:
    """
    Converts ISO 8601 date string into a ``date`` object.
    Expected format is  "2014-09-05"

    Args:
        value: date string e.g. "2014-09-05"
    """
    return datetime.strptime(value, "%Y-%m-%d").date()


def attachment(url: str, filename="") -> dict:
    """
    Returns a dictionary using the expected dicitonary format for attachments.

    When creating an attachment, ``url`` is required, and ``filename`` is optional.
    Airtable will download the file at the given url and keep its own copy of it.
    All other attachment object properties will be generated server-side soon afterward.

    Note:
        Attachment field values muest be **an array of objects**.

    Usage:
        >>> table = Table(...)
        >>> profile_url = "https://myprofile.com/id/profile.jpg
        >>> rec = table.create({"Profile Photo": [attachment(profile_url)]})
        {
            'id': 'recZXOZ5gT9vVGHfL',
            'fields': {
                'attachment': [
                    {
                        'id': 'attu6kbaST3wUuNTA',
                        'url': 'https://aws1.discourse-cdn.com/airtable/original/2X/4/411e4fac00df06a5e316a0585a831549e11d0705.png',
                        'filename': '411e4fac00df06a5e316a0585a831549e11d0705.png'
                    }
                ]
            },
            'createdTime': '2021-08-21T22:28:36.000Z'
        }


    """
    return {"url": url} if not filename else {"url": url, "filename": filename}


class AutoRetrySession(Session):
    """ This Session object will retry requests that return temporary errors. """

    DEFAULT_RETRY_CODES = (429, 500, 502, 503, 504)
    DEFAULT_RETRY_METHODS = ("HEAD", "GET", "POST", "PUT", "PATCH", "OPTIONS", "DELETE")
    DEFAULT_BACKOFF_FACTOR = 0.3
    API_CLIENT_MAX_RETRIES = 5
    API_CLIENT_POOL_CONNECTIONS = 30
    API_CLIENT_MAX_POOL_SIZE = 30

    def __init__(self, status_force: tuple = DEFAULT_RETRY_CODES, method_whitelist: tuple = DEFAULT_RETRY_METHODS,
                 max_retries: int = API_CLIENT_MAX_RETRIES, backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
                 pool_connections: int = API_CLIENT_POOL_CONNECTIONS, pool_maxsize: int = API_CLIENT_MAX_POOL_SIZE,
                 prefixes: tuple = ('http://', 'https://')):
        super().__init__()

        # Indicate our preference for JSON
        self.headers.update({"Accept": "application/json",
                             'User-Agent': f'pyairtable client {pyairtable_version}'})

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=list(status_force),
            method_whitelist=list(method_whitelist),
            raise_on_status=False,  # type: ignore
        )

        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )
        for url in prefixes:
            super(AutoRetrySession, self).mount(url, adapter)
