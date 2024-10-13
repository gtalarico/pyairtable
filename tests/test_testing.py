import re
from unittest.mock import ANY

from pyairtable import testing as T


def test_fake_id():
    assert re.match(r"rec[a-zA-Z0-9]{14}", T.fake_id())
    assert T.fake_id(value=123) == "rec00000000000123"
    assert T.fake_id("tbl", "x") == "tbl0000000000000x"


def test_fake_record():
    assert T.fake_record(id=123) == {
        "id": "rec00000000000123",
        "createdTime": ANY,
        "fields": {},
    }
    assert T.fake_record(id="recABC00000000123") == {
        "id": "recABC00000000123",
        "createdTime": ANY,
        "fields": {},
    }
    assert T.fake_record({"A": 1}, 123) == {
        "id": "rec00000000000123",
        "createdTime": ANY,
        "fields": {"A": 1},
    }
    assert T.fake_record(one=1, two=2) == {
        "id": ANY,
        "createdTime": ANY,
        "fields": {"one": 1, "two": 2},
    }


def test_fake_user():
    user = T.fake_user()
    assert user == {
        "id": ANY,
        "email": f"{user['id'].lower()}@example.com",
        "name": "Fake User",
    }
    assert T.fake_user("Alice") == {
        "id": "usr000000000Alice",
        "email": "alice@example.com",
        "name": "Alice",
    }


def test_fake_attachment():
    assert T.fake_attachment() == {
        "id": ANY,
        "url": "https://example.com/",
        "filename": "foo.txt",
        "size": 100,
        "type": "text/plain",
    }
    assert T.fake_attachment(url="https://example.com/image.png") == {
        "id": ANY,
        "url": "https://example.com/image.png",
        "filename": "image.png",
        "size": 100,
        "type": "image/png",
    }
    assert T.fake_attachment(url="https://example.com", filename="image.png") == {
        "id": ANY,
        "url": "https://example.com",
        "filename": "image.png",
        "size": 100,
        "type": "image/png",
    }


def test_coerce_fake_record():
    assert T.coerce_fake_record({"Name": "Alice"}) == {
        "id": ANY,
        "createdTime": ANY,
        "fields": {"Name": "Alice"},
    }
    assert T.coerce_fake_record({"fields": {"Name": "Alice"}}) == {
        "id": ANY,
        "createdTime": ANY,
        "fields": {"Name": "Alice"},
    }
    assert T.coerce_fake_record({"id": "rec123", "fields": {"Name": "Alice"}}) == {
        "id": "rec123",
        "createdTime": ANY,
        "fields": {"Name": "Alice"},
    }
    assert T.coerce_fake_record(fake := T.fake_record()) == fake
