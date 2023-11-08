from unittest.mock import ANY, call

import pytest

from pyairtable import testing as T


@pytest.mark.parametrize(
    "funcname,sig,expected",
    [
        ("fake_id", call(value=123), "rec00000000000123"),
        ("fake_id", call("tbl", "x"), "tbl0000000000000x"),
        (
            "fake_record",
            call(id=123),
            {"id": "rec00000000000123", "createdTime": ANY, "fields": {}},
        ),
        (
            "fake_record",
            call({"A": 1}, 123),
            {"id": "rec00000000000123", "createdTime": ANY, "fields": {"A": 1}},
        ),
        (
            "fake_record",
            call(one=1, two=2),
            {
                "id": ANY,
                "createdTime": ANY,
                "fields": {"one": 1, "two": 2},
            },
        ),
        (
            "fake_user",
            call("alice"),
            {
                "id": "usr000000000alice",
                "email": "alice@example.com",
                "name": "Fake User",
            },
        ),
    ],
)
def test_fake_function(funcname, sig, expected):
    func = getattr(T, funcname)
    assert func(*sig.args, **sig.kwargs) == expected
