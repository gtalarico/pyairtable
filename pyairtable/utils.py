from datetime import date, datetime
from typing import Union


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
