from datetime import date, datetime
from typing import Iterator, Sequence, TypeVar, Union

from pyairtable.api.types import CreateAttachmentDict

T = TypeVar("T")


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
    Convert an ISO 8601 datetime string into a ``datetime`` object.

    Args:
        value: datetime string, e.g. "2014-09-05T07:00:00.000Z"
    """
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")


def date_to_iso_str(value: Union[date, datetime]) -> str:
    """
    Converts a ``date`` or ``datetime`` into an Airtable-compatible ISO 8601 string

    Args:
        value: date or datetime object, e.g. "2014-09-05"
    """
    return value.strftime("%Y-%m-%d")


def date_from_iso_str(value: str) -> date:
    """
    Converts ISO 8601 date string into a ``date`` object.

    Args:
        value: date string, e.g. "2014-09-05"
    """
    return datetime.strptime(value, "%Y-%m-%d").date()


def attachment(url: str, filename: str = "") -> CreateAttachmentDict:
    """
    Returns a dictionary using the expected dictionary format for creating attachments.

    When creating an attachment, ``url`` is required, and ``filename`` is optional.
    Airtable will download the file at the given url and keep its own copy of it.
    All other attachment object properties will be generated server-side soon afterward.

    Note:
        Attachment field values **must** be an array of
        :class:`~pyairtable.api.types.AttachmentDict` or
        :class:`~pyairtable.api.types.CreateAttachmentDict`;
        it is not valid to pass a single item to the API.

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


def chunked(iterable: Sequence[T], chunk_size: int) -> Iterator[Sequence[T]]:
    """
    Break a sequence into chunks.

    Args:
        iterable: Any sequence.
        chunk_size: Maximum items to yield per chunk.
    """
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i : i + chunk_size]
