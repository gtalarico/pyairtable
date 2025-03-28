from datetime import datetime, timezone

import pytest

from pyairtable.orm import Model
from pyairtable.orm import fields as f
from pyairtable.testing import fake_meta

pytestmark = [pytest.mark.integration]


class _Address(Model):
    Meta = fake_meta()

    number = f.IntegerField("Number")
    street = f.TextField("Street")
    contact = f.LinkField["_Contact"](
        "Contact",
        model="test_integration_orm._Contact",
        lazy=True,
    )


class _Contact(Model):
    Meta = fake_meta()

    first_name = f.TextField("First Name")
    last_name = f.TextField("Last Name")
    email = f.EmailField("Email")
    is_registered = f.CheckboxField("Registered")
    address = f.LinkField("Address", _Address, lazy=True)
    birthday = f.DateField("Birthday")
    last_access = f.DatetimeField("Last Access")


class _Everything(Model):
    Meta = fake_meta()

    name = f.TextField("Name")
    notes = f.RichTextField("Notes")
    assignee = f.CollaboratorField("Assignee")
    watchers = f.MultipleCollaboratorsField("Watchers")
    status = f.SelectField("Status")
    attachments = f.AttachmentsField("Attachments")
    done = f.CheckboxField("Done")
    tags = f.MultipleSelectField("Tags")
    date = f.DateField("Date")
    datetime = f.DatetimeField("DateTime")
    duration_hmm = f.DurationField("Duration (h:mm)")
    duration_hmmsss = f.DurationField("Duration (h:mm:ss.s)")
    phone = f.PhoneNumberField("Phone")
    email = f.EmailField("Email")
    url = f.UrlField("URL")
    integer = f.IntegerField("Integer")
    decimal = f.FloatField("Decimal 1")
    number = f.NumberField("Decimal 2")
    autonumber = f.AutoNumberField("Autonumber")
    dollars = f.CurrencyField("Dollars")
    percent = f.PercentField("Percent")
    stars = f.RatingField("Stars")
    barcode = f.BarcodeField("Barcode")
    button = f.ButtonField("Open URL")
    formula_integer = f.IntegerField("Formula Int", readonly=True)
    formula_float = f.FloatField("Formula Float", readonly=True)
    formula_text = f.TextField("Formula Text", readonly=True)
    formula_error = f.TextField("Formula Error", readonly=True)
    formula_nan = f.TextField("Formula NaN", readonly=True)
    addresses = f.LinkField("Address", _Address)
    link_count = f.CountField("Link to Self (Count)")
    link_self = f.SingleLinkField["_Everything"](
        "Link to Self",
        model="test_integration_orm._Everything",
        lazy=False,
    )
    rollup_integer = f.IntegerField("Rollup Int", readonly=True)
    rollup_error = f.TextField("Rollup Error", readonly=True)
    lookup_integer = f.LookupField("Lookup Int", readonly=True)
    lookup_error = f.LookupField("Lookup Error", readonly=True)
    created = f.CreatedTimeField("Created")
    created_by = f.CreatedByField("Created By")
    last_modified = f.LastModifiedTimeField("Last Modified")
    last_modified_by = f.LastModifiedByField("Last Modified By")
    required_barcode = f.RequiredBarcodeField("Barcode")
    required_collaborator = f.RequiredCollaboratorField("Assignee")
    required_count = f.RequiredCountField("Count")
    required_currency = f.RequiredCurrencyField("Dollars")
    required_date = f.RequiredDateField("Date")
    required_datetime = f.RequiredDatetimeField("DateTime")
    required_duration = f.RequiredDurationField("Duration (h:mm)")
    required_email = f.RequiredEmailField("Email")
    required_float = f.RequiredFloatField("Decimal 1")
    required_integer = f.RequiredIntegerField("Integer")
    required_number = f.RequiredNumberField("Number")
    required_percent = f.RequiredPercentField("Percent")
    required_phone = f.RequiredPhoneNumberField("Phone")
    required_rating = f.RequiredRatingField("Stars")
    required_rich_text = f.RequiredRichTextField("Notes")
    required_select = f.RequiredSelectField("Status")
    required_text = f.RequiredTextField("Name")
    required_url = f.RequiredUrlField("URL")


def _model_fixture(cls, monkeypatch, make_meta):
    monkeypatch.setattr(cls, "Meta", make_meta(cls.__name__.replace("_", "")))
    yield cls
    for page in cls.meta.table.iterate():
        cls.meta.table.batch_delete([record["id"] for record in page])


@pytest.fixture
def Everything(monkeypatch, make_meta):
    yield from _model_fixture(_Everything, monkeypatch, make_meta)


@pytest.fixture
def Address(monkeypatch, make_meta):
    yield from _model_fixture(_Address, monkeypatch, make_meta)


@pytest.fixture
def Contact(monkeypatch, make_meta):
    yield from _model_fixture(_Contact, monkeypatch, make_meta)


def test_integration_orm(Contact, Address):
    STREET = "123 Han"
    address = Address(street=STREET)
    address.save()

    contact = Contact(
        first_name="John",
        last_name="LastName",
        email="email@email.com",
        is_registered=True,
        address=[address],
        birthday=datetime.now(timezone.utc).date(),
        last_access=datetime.now(timezone.utc),
    )

    assert contact.first_name == "John"
    assert contact.save().created
    assert contact.id

    contact.first_name = "Not Gui"
    assert not contact.save().created

    rv_address = contact.address[0]
    assert rv_address.exists()

    assert rv_address.id == contact.address[0].id == address.id

    # Fetching
    contact = Contact.from_id(contact.id, fetch=False)
    assert not contact.address
    assert not contact.fetch()
    rv_address_2 = contact.address[0]
    assert not rv_address_2.street
    rv_address_2.fetch()
    assert rv_address_2.street == rv_address.street == STREET


def test_undeclared_fields(make_meta):
    """
    Test that if our ORM is missing some fields, it does not fail on retrieval
    and does not clobber their values on save.
    """

    class Contact(Model):
        Meta = make_meta("Contact")
        first_name = f.TextField("First Name")
        last_name = f.TextField("Last Name")

    table = Contact.meta.table
    record = table.create(
        {
            "First Name": "Alice",
            "Last Name": "Arnold",
            "Email": "alice@example.com",
            "Birthday": "1970-01-01",
        }
    )

    # This should not raise an exception
    contact = Contact.from_id(record["id"])

    # This should not clobber the values in 'Email' or 'Birthday'
    contact.save()
    assert table.get(record["id"]) == record


def test_every_field(Everything):
    """
    Integration test for the ORM that exercises every supported field type.
    """
    # Validate there are no field types we skipped
    classes_used = {
        type(field) for field in vars(Everything).values() if isinstance(field, f.Field)
    }
    for field_class in f.ALL_FIELDS:
        if field_class in {
            f.ExternalSyncSourceField,
            f.AITextField,
            f.RequiredAITextField,
            f.ManualSortField,
            # These are so similar to TextField we don't need to integration test them
            f.SingleLineTextField,
            f.MultilineTextField,
            f.RequiredSingleLineTextField,
            f.RequiredMultilineTextField,
        }:
            continue
        assert field_class in classes_used

    record: _Everything = Everything(
        name=None,
        notes=None,
        assignee=None,
        status=None,
        attachments=None,
        done=None,
        tags=None,
        date=None,
        datetime=None,
        duration_hmm=None,
        duration_hmmsss=None,
        phone=None,
        email=None,
        url=None,
        integer=None,
        decimal=None,
        number=None,
        dollars=None,
        percent=None,
        stars=None,
        barcode=None,
        addresses=None,
        link_self=None,
    )
    assert not record.id
    record.save()
    assert record.id
    assert record.addresses == []
    assert record.link_self is None
    record.link_self = record
    record.save()

    # The ORM won't refresh the model's field values after save()
    assert record.formula_integer is None
    assert record.formula_nan == ""
    assert record.link_count is None
    assert record.lookup_error == []
    assert record.lookup_integer == []
    record.fetch()
    assert record.formula_integer is not None
    assert record.formula_nan == {"specialValue": "NaN"}
    assert record.link_count == 1
    assert record.lookup_error == [{"error": "#ERROR!"}]
    assert record.lookup_integer == [record.formula_integer]


def test_attachments_upload(Everything, valid_img_url, tmp_path):
    record: _Everything = Everything()
    record.save()

    # add an attachment via URL
    record.attachments.append({"url": valid_img_url, "filename": "logo.png"})
    record.save()
    assert record.attachments[0]["url"] == valid_img_url
    record.fetch()
    assert record.attachments[0]["id"] is not None
    assert record.attachments[0]["filename"] == "logo.png"

    # add an attachment by uploading content
    tmp_file = tmp_path / "sample.txt"
    tmp_file.write_text("Hello, World!")
    record.attachments.upload(tmp_file)
    # ensure we got all attachments, not just the latest one
    assert record.attachments[0]["filename"] == "logo.png"
    assert record.attachments[0]["type"] == "image/png"
    assert record.attachments[1]["filename"] == "sample.txt"
    assert record.attachments[1]["type"] == "text/plain"

    # ensure everything persists/loads correctly after fetch()
    record.fetch()
    assert record.attachments[0]["filename"] == "logo.png"
    assert record.attachments[0]["type"] == "image/png"
    assert record.attachments[1]["filename"] == "sample.txt"
    assert record.attachments[1]["type"] == "text/plain"
