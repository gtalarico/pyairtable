import re
from datetime import datetime, timezone
from functools import partial
from operator import itemgetter
from unittest import mock

import pytest
from requests_mock import Mocker

from pyairtable import Table
from pyairtable.orm import Model
from pyairtable.orm import fields as f
from pyairtable.testing import fake_meta, fake_record
from pyairtable.utils import datetime_to_iso_str

NOW = datetime.now().isoformat() + "Z"


class Address(Model):
    Meta = fake_meta(table_name="Address")
    street = f.TextField("Street")
    number = f.IntegerField("Number")


class Contact(Model):
    Meta = fake_meta(table_name="Contact")
    first_name = f.TextField("First Name")
    last_name = f.TextField("Last Name")
    email = f.EmailField("Email")
    is_registered = f.CheckboxField("Registered?")
    address = f.LinkField("Link", Address, lazy=False)
    birthday = f.DateField("Birthday")
    created_at = f.CreatedTimeField("Created At")


@pytest.fixture
def contact_record():
    return fake_record(
        {
            "First Name": "John",
            "Last Name": "Doe",
            "Email": "john@example.com",
            "Registered?": True,
            "Birthday": "1970-01-01",
        }
    )


def test_model_basics():
    contact = Contact(
        first_name="Gui",
        last_name="Talarico",
        email="gui@gui.com",
        is_registered=True,
        birthday=datetime(2020, 12, 12).date(),
    )

    # attribute look up
    assert contact.first_name == "Gui"
    assert not contact.id

    # save
    with mock.patch.object(Table, "create") as m_save:
        m_save.return_value = {"id": "id", "createdTime": NOW}
        assert contact.save().created

    assert m_save.called
    assert contact.id == "id"
    assert contact.created_time.tzinfo is timezone.utc

    # delete
    with mock.patch.object(Table, "delete") as m_delete:
        m_delete.return_value = {"deleted": True}
        contact.delete()

    assert m_delete.called

    # cannot save a deleted record
    with pytest.raises(RuntimeError):
        contact.save()

    record = contact.to_record()
    assert record["id"] == contact.id
    assert record["createdTime"] == datetime_to_iso_str(contact.created_time)
    assert record["fields"]["First Name"] == contact.first_name


def test_unsupplied_fields():
    """
    Test that we can create a record without fields.
    """
    a = Address()
    assert a.number is None
    assert a.street == ""


def test_null_fields():
    """
    Test that we can create a record with null fields.
    """
    a = Address(number=None, street=None)
    assert a.number is None
    assert a.street == ""


def test_first():
    with mock.patch.object(Table, "first") as m_first:
        m_first.return_value = {
            "id": "recwnBLPIeQJoYVt4",
            "createdTime": NOW,
            "fields": {
                "First Name": "X",
                "Created At": "2014-09-05T12:34:56.000Z",
            },
        }
        contact = Contact.first()

    assert contact.first_name == "X"


def test_first_none():
    with mock.patch.object(Table, "first") as m_first:
        m_first.return_value = None
        contact = Contact.first()

    assert contact is None


def test_from_record():
    # Fetch = True
    with mock.patch.object(Table, "get") as m_get:
        m_get.return_value = {
            "id": "recwnBLPIeQJoYVt4",
            "createdTime": NOW,
            "fields": {
                "First Name": "X",
                "Birthday": None,
                "Created At": "2014-09-05T12:34:56.000Z",
            },
        }
        contact = Contact.from_id("recwnBLPIeQJoYVt4")

    assert m_get.called
    assert contact.id == "recwnBLPIeQJoYVt4"
    assert contact.first_name == "X"
    assert contact.created_at.year == 2014

    # Fetch = False
    with mock.patch.object(Table, "get") as m_get_no_fetch:
        contact = Contact.from_id("recwnBLPIeQJoYVt4", fetch=False)
        assert not m_get_no_fetch.called
        assert not contact.first_name == "X"


def test_unmodified_field_not_saved(contact_record):
    """
    Test that we do not attempt to save fields to the API if they are unchanged.
    """
    contact = Contact.from_record(contact_record)
    mock_update_contact = partial(
        mock.patch.object, Table, "update", return_value=contact_record
    )

    # Do not call update() if the record is unchanged
    with mock_update_contact() as m_update:
        result = contact.save()
        assert not (result.created or result.updated)
        m_update.assert_not_called()

    # By default, only pass fields which were changed to the API
    with mock_update_contact() as m_update:
        contact.email = "john.doe@example.com"
        contact.save()
        m_update.assert_called_once_with(
            contact.id,
            {"Email": "john.doe@example.com"},
            typecast=True,
            use_field_ids=False,
        )

    # Once saved, the field is no longer marked as changed
    with mock_update_contact() as m_update:
        contact.save()
        m_update.assert_not_called()

    # We can explicitly pass all fields to the API
    with mock_update_contact() as m_update:
        contact.save(force=True)
        m_update.assert_called_once_with(
            contact.id,
            {
                "First Name": "John",
                "Last Name": "Doe",
                "Email": "john.doe@example.com",
                "Registered?": True,
                "Birthday": "1970-01-01",
            },
            typecast=True,
            use_field_ids=False,
        )


def test_linked_record():
    record = {"id": "recFake", "createdTime": NOW, "fields": {"Street": "A"}}
    address = Address.from_id("recFake", fetch=False)

    # Id Reference
    contact = Contact(address=[address])
    assert contact.address[0].id == address.id
    assert not contact.address[0].street

    with Mocker() as mock:
        url = Address.meta.table.urls.record(address.id)
        mock.get(url, status_code=200, json=record)
        contact.address[0].fetch()

    assert contact.address[0].street == "A"


@pytest.mark.parametrize("access_linked_records", (True, False))
def test_linked_record_can_be_saved(requests_mock, access_linked_records):
    """
    Test that we can call Model.save() on a model with a non-lazy linked field,
    whether we've already accessed the field contents or not.

    Accessing the linked field converts its internal representation from
    record IDs into instances of the model. This could interfere with save(),
    so this test ensures we don't regress the capability.
    """
    address_json = fake_record(Number=123, Street="Fake St")
    address_id = address_json["id"]
    address_url_re = re.escape(Address.meta.table.urls.records + "?filterByFormula=")
    contact_json = fake_record(Email="alice@example.com", Link=[address_id])
    contact_id = contact_json["id"]
    contact_url = Contact.meta.table.urls.record(contact_id)
    contact_url_re = re.escape(Contact.meta.table.urls.records + "?filterByFormula=")
    requests_mock.get(re.compile(address_url_re), json={"records": [address_json]})
    requests_mock.get(re.compile(contact_url_re), json={"records": [contact_json]})
    requests_mock.get(contact_url, json=contact_json)
    mock_save = requests_mock.patch(contact_url, json=contact_json)

    contact = Contact.from_id(contact_id)

    if access_linked_records:
        assert contact.address[0].id == address_id

    contact.save(force=True)
    assert mock_save.last_request.json() == {
        "fields": {
            "Email": "alice@example.com",
            "Link": [address_id],
        },
        "typecast": True,
        "returnFieldsByFieldId": False,
    }


def test_save__raise_on_unsaved_link(requests_mock):
    """
    Test that Model.save() raises an exception if called before saving all linked records.
    """
    contact = Contact(address=[Address()])

    with pytest.raises(ValueError) as ctx:
        contact.save()

    assert "Contact.address contains an unsaved record" in ctx.exconly()


@pytest.mark.parametrize(
    "test_case",
    [
        ("from_id", lambda cls, id: cls.from_id(id)),
        ("first", lambda cls, _: cls.first()),
        ("all", lambda cls, _: cls.all()[0]),
    ],
    ids=itemgetter(0),
)
def test_undeclared_field(requests_mock, test_case):
    """
    Test that Model methods which fetch data from the Airtable API will
    ignore any fields which are missing from the Model definition.

    See https://github.com/gtalarico/pyairtable/issues/190
    """

    record = fake_record(
        Number=123,
        Street="Fake St",
        City="Springfield",
        State="IL",
    )

    requests_mock.get(
        Address.meta.table.urls.records,
        status_code=200,
        json={"records": [record]},
    )
    requests_mock.get(
        Address.meta.table.urls.record(record["id"]),
        status_code=200,
        json=record,
    )

    _, get_model_instance = test_case
    instance = get_model_instance(Address, record["id"])
    assert instance.to_record()["fields"] == {"Number": 123, "Street": "Fake St"}


@mock.patch("pyairtable.Table.batch_create")
@mock.patch("pyairtable.Table.batch_update")
def test_batch_save(mock_update, mock_create):
    """
    Test that we can pass multiple unsaved Model instances (or dicts) to batch_save
    and it will create or update them all in as few requests as possible.
    """
    addr1 = Address(number=123, street="Fake St")
    addr2 = Address(number=456, street="Fake St")
    addr3 = Address.from_record(
        {
            "id": "recExistingRecord",
            "createdTime": datetime.now(timezone.utc).isoformat(),
            "fields": {"Number": 789, "Street": "Fake St"},
        }
    )

    mock_create.return_value = [
        fake_record(id="abc", Number=123, Street="Fake St"),
        fake_record(id="def", Number=456, Street="Fake St"),
    ]

    # Just like model.save(), Model.batch_save() will set IDs on new records.
    Address.batch_save([addr1, addr2, addr3])
    assert addr1.id == "rec00000000000abc"
    assert addr2.id == "rec00000000000def"
    assert addr3.id == "recExistingRecord"

    mock_create.assert_called_once_with(
        [
            {"Number": 123, "Street": "Fake St"},
            {"Number": 456, "Street": "Fake St"},
        ],
        typecast=True,
        use_field_ids=False,
    )
    mock_update.assert_called_once_with(
        [
            {
                "id": "recExistingRecord",
                "fields": {"Number": 789, "Street": "Fake St"},
            },
        ],
        typecast=True,
        use_field_ids=False,
    )


@mock.patch("pyairtable.Table.batch_create")
@mock.patch("pyairtable.Table.batch_update")
def test_batch_save__only_create(mock_update, mock_create):
    Address.batch_save([Address(), Address()])
    assert mock_create.call_count == 1
    assert mock_update.call_count == 0


@mock.patch("pyairtable.Table.batch_create")
@mock.patch("pyairtable.Table.batch_update")
def test_batch_save__only_update(mock_update, mock_create):
    a1 = Address.from_record(fake_record())
    a2 = Address.from_record(fake_record())
    Address.batch_save([a1, a2])
    assert mock_create.call_count == 0
    assert mock_update.call_count == 1


@mock.patch("pyairtable.Table.batch_create")
@mock.patch("pyairtable.Table.batch_update")
def test_batch_save__invalid_class(mock_update, mock_create):
    """
    Test that batch_save() raises TypeError if a model is given which is not an
    instance of the model being called.
    """
    with pytest.raises(TypeError):
        Address.batch_save([Contact()])

    assert mock_update.call_count == 0
    assert mock_create.call_count == 0


@mock.patch("pyairtable.Table.batch_create")
@mock.patch("pyairtable.Table.batch_update")
def test_batch_save__raise_on_unsaved_link(mock_update, mock_create):
    """
    Test that Model.batch_save() raises ValueError if called before
    all linked records have been saved.
    """
    contacts = [Contact() for _ in range(20)]
    contacts[14].address = [Address()]

    with pytest.raises(ValueError) as ctx:
        Contact.batch_save(contacts)

    assert "Contact.address contains an unsaved record" in ctx.exconly()
    assert mock_update.call_count == 0
    assert mock_create.call_count == 0


@mock.patch("pyairtable.Table.batch_delete")
def test_batch_delete(mock_delete):
    """
    Test that we can pass a list of models to Model.batch_delete.
    """
    addresses = [
        Address.from_record(fake_record(id=n, Number=str(n), Street="Fake St"))
        for n in range(20)
    ]
    Address.batch_delete(addresses)
    mock_delete.assert_called_once_with([record.id for record in addresses])


@mock.patch("pyairtable.Table.batch_delete")
def test_batch_delete__unsaved_record(mock_delete):
    """
    Test that we get a ValueError (and make no deletions) if Model.batch_delete
    receives any models which have not been created yet.
    """
    addresses = [
        Address.from_record(fake_record(Number=1, Street="Fake St")),
        Address(number=2, street="Fake St"),
    ]
    with pytest.raises(ValueError):
        Address.batch_delete(addresses)

    assert mock_delete.call_count == 0


@mock.patch("pyairtable.Table.batch_delete")
def test_batch_delete__invalid_class(mock_delete):
    """
    Test that batch_delete() raises TypeError if a model is given which is not an
    instance of the model being called.
    """
    with pytest.raises(TypeError):
        Address.batch_delete([Contact.from_record(fake_record())])

    assert mock_delete.call_count == 0
