import pytest
from pydantic import ValidationError

from pyairtable.api import types as T
from pyairtable.testing import fake_attachment, fake_id, fake_record, fake_user


@pytest.mark.parametrize(
    "cls,value",
    [
        (T.AttachmentDict, fake_attachment()),
        (T.BarcodeDict, {"type": "upc", "text": "0123456"}),
        (T.BarcodeDict, {"text": "0123456"}),
        (T.ButtonDict, {"label": "My Button", "url": "http://example.com"}),
        (T.ButtonDict, {"label": "My Button", "url": None}),
        (T.CollaboratorDict, fake_user()),
        (T.CreateAttachmentDict, {"url": "http://example.com", "filename": "test.jpg"}),
        (T.CreateAttachmentDict, {"url": "http://example.com"}),
        (T.CreateRecordDict, {"fields": {}}),
        (T.RecordDeletedDict, {"deleted": True, "id": fake_id()}),
        (T.RecordDict, fake_record()),
        (T.UpdateRecordDict, {"id": fake_id(), "fields": {}}),
        # Test that we won't fail if Airtable adds new fields in the fuutre
        (T.RecordDict, {**fake_record(), "comments": []}),
    ],
)
def test_assert_typed_dict(cls, value):
    """
    Test that we can assert that a dict does conform to a TypedDict.
    """
    T.assert_typed_dict(cls, value)
    T.assert_typed_dicts(cls, [value])
    # Test that a mix of valid and invalid values still raises an exception
    with pytest.raises(TypeError):
        T.assert_typed_dicts(cls, [value, -1])


@pytest.mark.parametrize(
    "cls,value",
    [
        (T.AttachmentDict, {}),
        (T.BarcodeDict, {"type": "upc"}),
        (T.ButtonDict, {}),
        (T.CollaboratorDict, {}),
        (T.CreateAttachmentDict, {}),
        (T.CreateRecordDict, {}),
        (T.RecordDeletedDict, {}),
        (T.RecordDict, {}),
        (T.UpdateRecordDict, {}),
    ],
)
def test_assert_not_typed_dict(cls, value):
    """
    Test that we can assert that a dict does *not* conform to a TypedDict.
    """
    with pytest.raises(ValidationError):
        T.assert_typed_dict(cls, value)
    with pytest.raises(ValidationError):
        T.assert_typed_dicts(cls, [value])


def test_assert_typed_dict__wrong_type():
    # assert_typed_dict() with a non-dict
    with pytest.raises(TypeError):
        T.assert_typed_dict(T.RecordDict, -1)
    # assert_typed_dicts() with a list of non-dict objects
    with pytest.raises(TypeError):
        T.assert_typed_dicts(T.RecordDict, [-1])
    # assert_typed_dicts() with a non-list
    with pytest.raises(TypeError):
        T.assert_typed_dicts(T.RecordDict, object())


@pytest.mark.parametrize(
    "value,is_error",
    [
        (None, False),
        (1, False),
        ("str", False),
        ({}, False),
        ({"error": "#ERROR!"}, True),
        ({"specialValue": "NaN"}, True),
    ],
)
def test_is_airtable_error(value, is_error):
    assert T.is_airtable_error(value) is is_error
