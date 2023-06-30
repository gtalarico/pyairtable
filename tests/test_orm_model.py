import mock
import pytest

from pyairtable.orm import Model
from pyairtable.orm import fields as f
from pyairtable.testing import fake_meta, fake_record


@pytest.fixture(autouse=True)
def no_requests(requests_mock):
    """
    Fail if any tests in this module try to make network calls.
    """


def test_model_missing_meta():
    """
    Test that we throw an exception if Meta is missing.
    """
    with pytest.raises(AttributeError):

        class Address(Model):
            street = f.TextField("Street")


def test_model_missing_meta_attribute():
    """
    Test that we throw an exception if Meta is missing a required attribute.
    """
    with pytest.raises(ValueError):

        class Address(Model):
            street = f.TextField("Street")

            class Meta:
                base_id = "required"
                table_name = "required"
                # api_key = "required"


def test_model_empty_meta():
    """
    Test that we throw an exception when a required Meta attribute is None.
    """
    with pytest.raises(ValueError):

        class Address(Model):
            Meta = fake_meta(api_key=None)
            street = f.TextField("Street")


def test_model_overlapping():
    # Should raise error because conflicts with .exists()
    with pytest.raises(ValueError):

        class Address(Model):
            Meta = fake_meta()
            exists = f.TextField("Exists")  # clases with Model.exists()


def test_repr():
    class Contact(Model):
        Meta = fake_meta()

    record = fake_record()
    assert repr(Contact.from_record(record)) == f"<Contact id='{record['id']}'>"
    assert repr(Contact()) == "<unsaved Contact>"


@mock.patch("pyairtable.Table.get")
def test_from_id(mock_get):
    class Contact(Model):
        Meta = fake_meta()
        name = f.TextField("Name")

    fake_contact = fake_record(Name="Alice")
    mock_get.return_value = fake_contact
    contact = Contact.from_id(fake_contact["id"])
    assert contact.id == fake_contact["id"]
    assert contact.name == "Alice"


@mock.patch("pyairtable.Table.all")
def test_from_ids(mock_all):
    class Contact(Model):
        Meta = fake_meta()

    fake_records = [fake_record() for _ in range(10)]
    mock_all.return_value = fake_records

    fake_ids = [record["id"] for record in fake_records]
    contacts = Contact.from_ids(fake_ids)
    mock_all.assert_called_once()
    assert len(contacts) == len(fake_records)
    assert {c.id for c in contacts} == {r["id"] for r in fake_records}

    # Should raise KeyError because of the invalid ID
    mock_all.reset_mock()
    with pytest.raises(KeyError):
        Contact.from_ids(fake_ids + ["recDefinitelyNotValid"])
    mock_all.assert_called_once()
