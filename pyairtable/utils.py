from datetime import datetime, date
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
