from functools import partial
from unittest import mock

import pytest

from pyairtable.orm import Model
from pyairtable.orm import fields as f
from pyairtable.testing import fake_id, fake_meta, fake_record


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


def test_model_empty_meta_with_callable():
    """
    Test that we throw an exception when a required Meta attribute is
    defined as a callable which returns None.
    """

    class Address(Model):
        Meta = fake_meta(api_key=lambda: None)
        street = f.TextField("Street")

    with mock.patch("pyairtable.Table.first", return_value=fake_record()) as m:
        with pytest.raises(ValueError):
            Address.first()
        m.assert_not_called()


@pytest.mark.parametrize("name", ("exists", "id"))
def test_model_overlapping(name):
    """
    Test that we raise ValueError when a subclass of Model defines
    a field with the same name as one of Model's properties or methods.
    """
    with pytest.raises(ValueError):
        type(
            "Address",
            (Model,),
            {
                "Meta": fake_meta(),
                name: f.TextField(name),
            },
        )


class FakeModel(Model):
    Meta = fake_meta()
    one = f.TextField("one")
    two = f.TextField("two")


def test_repr():
    record = fake_record()
    assert repr(FakeModel.from_record(record)) == f"<FakeModel id='{record['id']}'>"
    assert repr(FakeModel()) == "<unsaved FakeModel>"


def test_delete():
    obj = FakeModel.from_record(record := fake_record())
    with mock.patch("pyairtable.Table.delete") as mock_delete:
        obj.delete()

    mock_delete.assert_called_once_with(record["id"])


def test_delete__unsaved():
    obj = FakeModel()
    with pytest.raises(ValueError):
        obj.delete()


def test_fetch():
    obj = FakeModel(id=fake_id())
    assert not obj.one
    assert not obj.two

    with mock.patch("pyairtable.Table.get") as mock_get:
        mock_get.return_value = fake_record(one=1, two=2)
        obj.fetch()

    assert obj.one == 1
    assert obj.two == 2


def test_fetch__unsaved():
    obj = FakeModel()
    with pytest.raises(ValueError):
        obj.fetch()


@pytest.mark.parametrize(
    "method,args",
    [
        ("comments", []),
        ("add_comment", ["Hello!"]),
    ],
)
def test_model_comment_method(method, args):
    """
    Test that comments() and add_comment() are passthroughs to Table.
    """
    record_id = fake_id()
    instance = FakeModel.from_id(record_id, fetch=False)
    with mock.patch(f"pyairtable.Table.{method}") as mock_method:
        result = getattr(instance, method)(*args)

    assert result == mock_method.return_value
    mock_method.assert_called_once_with(record_id, *args)


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
    fake_records = [fake_record() for _ in range(10)]
    mock_all.return_value = fake_records

    fake_ids = [record["id"] for record in fake_records]
    contacts = FakeModel.from_ids(fake_ids)
    mock_all.assert_called_once()
    assert len(contacts) == len(fake_records)
    assert {c.id for c in contacts} == {r["id"] for r in fake_records}

    # Should raise KeyError because of the invalid ID
    mock_all.reset_mock()
    with pytest.raises(KeyError):
        FakeModel.from_ids(fake_ids + ["recDefinitelyNotValid"])
    mock_all.assert_called_once()


@mock.patch("pyairtable.Table.all")
def test_from_ids__no_fetch(mock_all):
    fake_ids = [fake_id() for _ in range(10)]
    contacts = FakeModel.from_ids(fake_ids, fetch=False)
    assert mock_all.call_count == 0
    assert len(contacts) == 10
    assert set(contact.id for contact in contacts) == set(fake_ids)


def test_dynamic_model_meta():
    """
    Test that we can provide callables in our Meta class to provide
    the access token, base ID, and table name at runtime. Also ensure
    that callable Meta attributes don't get called until they're needed.
    """
    data = {
        "api_key": "FakeApiKey",
        "base_id": "appFakeBaseId",
        "table_name": "tblFakeTableName",
    }

    class Fake(Model):
        class Meta:
            api_key = lambda: data["api_key"]  # noqa
            base_id = partial(data.get, "base_id")
            table_name = mock.Mock(return_value=data["table_name"])

    f = Fake()
    Fake.Meta.table_name.assert_not_called()

    assert f._get_meta("api_key") == data["api_key"]
    assert f._get_meta("base_id") == data["base_id"]
    assert f._get_meta("table_name") == data["table_name"]
    Fake.Meta.table_name.assert_called_once()
