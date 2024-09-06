from datetime import date, datetime, timezone
from functools import partial

import pytest

from pyairtable import utils
from pyairtable.testing import fake_record

utc_tz = partial(datetime, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "dt_obj,dt_str",
    [
        (datetime(2000, 1, 2, 3, 4, 5, 0), "2000-01-02T03:04:05.000"),
        (datetime(2025, 12, 31, 23, 59, 59, 0), "2025-12-31T23:59:59.000"),
        (datetime(2025, 12, 31, 23, 59, 59, 5_000), "2025-12-31T23:59:59.005"),
        (datetime(2025, 12, 31, 23, 59, 59, 555_000), "2025-12-31T23:59:59.555"),
        (utc_tz(2000, 1, 2, 3, 4, 5, 0), "2000-01-02T03:04:05.000Z"),
        (utc_tz(2025, 12, 31, 23, 59, 59, 0), "2025-12-31T23:59:59.000Z"),
        (utc_tz(2025, 12, 31, 23, 59, 59, 5_000), "2025-12-31T23:59:59.005Z"),
        (utc_tz(2025, 12, 31, 23, 59, 59, 555_000), "2025-12-31T23:59:59.555Z"),
    ],
)
def test_datetime_utils(dt_obj, dt_str):
    assert utils.datetime_to_iso_str(dt_obj) == dt_str
    assert utils.datetime_from_iso_str(dt_str) == dt_obj


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


@pytest.mark.parametrize(
    "func,value,expected",
    [
        (utils.is_airtable_id, -1, False),
        (utils.is_airtable_id, "appAkBDICXDqESDhF", True),
        (utils.is_airtable_id, "app0000000000Fake", True),
        (utils.is_airtable_id, "appWrongLength", False),
        (utils.is_record_id, "rec0000000000Fake", True),
        (utils.is_record_id, "app0000000000Fake", False),
        (utils.is_base_id, "app0000000000Fake", True),
        (utils.is_base_id, "rec0000000000Fake", False),
        (utils.is_table_id, "tbl0000000000Fake", True),
        (utils.is_table_id, "rec0000000000Fake", False),
        (utils.is_field_id, "fld0000000000Fake", True),
        (utils.is_field_id, "rec0000000000Fake", False),
    ],
)
def test_id_check(func, value, expected):
    assert func(value) is expected


@pytest.mark.parametrize(
    "func,input,expected",
    [
        (utils.coerce_iso_str, None, None),
        (utils.coerce_iso_str, "asdf", ValueError),
        (utils.coerce_iso_str, -1, TypeError),
        (utils.coerce_iso_str, "2023-01-01", "2023-01-01"),
        (utils.coerce_iso_str, "2023-01-01 12:34:56", "2023-01-01 12:34:56"),
        (utils.coerce_iso_str, date(2023, 1, 1), "2023-01-01"),
        (
            utils.coerce_iso_str,
            datetime(2023, 1, 1, 12, 34, 56),
            "2023-01-01T12:34:56",
        ),
        (utils.coerce_list_str, None, []),
        (utils.coerce_list_str, "asdf", ["asdf"]),
        (utils.coerce_list_str, ("one", "two", "three"), ["one", "two", "three"]),
        (utils.coerce_list_str, -1, TypeError),
    ],
)
def test_converter(func, input, expected):
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            func(input)
        return

    assert func(input) == expected


def test_fieldgetter():
    get_a = utils.fieldgetter("A")
    get_abc = utils.fieldgetter("A", "B", "C")

    assert get_a(fake_record(A=1)) == 1
    assert get_a({"fields": {"A": 1}}) == 1
    assert get_abc(fake_record(A=1, C=3)) == (1, None, 3)
    assert get_abc({"fields": {"A": 1, "C": 3}}) == (1, None, 3)

    record = fake_record(A="one", B="two")
    assert get_a(record) == "one"
    assert get_abc(record) == ("one", "two", None)
    assert utils.fieldgetter("id")(record) == record["id"]
    assert utils.fieldgetter("createdTime")(record) == record["createdTime"]


def test_fieldgetter__required():
    """
    Test that required=True means all fields are required.
    """
    require_ab = utils.fieldgetter("A", "B", required=True)
    record = fake_record(A="one", B="two")
    assert require_ab(record) == ("one", "two")
    with pytest.raises(KeyError):
        require_ab(fake_record(A="one"))


def test_fieldgetter__required_list():
    """
    Test that required=["A", "B"] means only A and B are required.
    """
    get_abc_require_ab = utils.fieldgetter("A", "B", "C", required=["A", "B"])
    record = fake_record(A="one", B="two")
    assert get_abc_require_ab(record) == ("one", "two", None)
    with pytest.raises(KeyError):
        get_abc_require_ab(fake_record(A="one", C="three"))


def test_fieldgetter__required_str():
    """
    Test that required="Bravo" means only Bravo is required,
    rather than ["B", "r", "a", "v", "o"].
    """
    get_abc_require_b = utils.fieldgetter("Alpha", "Bravo", required="Bravo")
    record = fake_record(Alpha="one", Bravo="two")
    assert get_abc_require_b(record) == ("one", "two")
    with pytest.raises(KeyError):
        get_abc_require_b(fake_record(Alpha="one"))
