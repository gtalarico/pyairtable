from datetime import date, datetime

import pytest

from pyairtable import utils


@pytest.mark.parametrize(
    "datetime_obj,datetime_str",
    [
        (datetime(2000, 1, 2, 3, 4, 5, 0), "2000-01-02T03:04:05.000Z"),
        (datetime(2025, 12, 31, 23, 59, 59, 0), "2025-12-31T23:59:59.000Z"),
        (datetime(2025, 12, 31, 23, 59, 59, 5_000), "2025-12-31T23:59:59.005Z"),
        (datetime(2025, 12, 31, 23, 59, 59, 555_000), "2025-12-31T23:59:59.555Z"),
    ],
)
def test_datetime_utils(datetime_obj, datetime_str):
    assert utils.datetime_to_iso_str(datetime_obj) == datetime_str
    assert utils.datetime_from_iso_str(datetime_str) == datetime_obj


@pytest.mark.parametrize(
    "date_obj,date_str",
    [
        (date(2000, 1, 2), "2000-01-02"),
        (date(2025, 12, 31), "2025-12-31"),
    ],
)
def test_date_utils(date_obj, date_str):
    assert utils.date_to_iso_str(date_obj) == date_str
    assert utils.date_from_iso_str(date_str) == date_obj


def test_attachment():
    assert utils.attachment("https://url.com") == {"url": "https://url.com"}
    assert utils.attachment("https://url.com", filename="test.jpg") == {
        "url": "https://url.com",
        "filename": "test.jpg",
    }
