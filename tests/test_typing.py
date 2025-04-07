"""
Tests that pyairtable.api functions/methods return appropriately typed responses.
"""

import datetime
from typing import TYPE_CHECKING, Iterator, List, Optional, Union

from typing_extensions import assert_type

import pyairtable
import pyairtable.api.types as T
import pyairtable.formulas as F
import pyairtable.orm.lists as L
import pyairtable.utils
from pyairtable import orm
from pyairtable.models import schema

if TYPE_CHECKING:
    # This section does not actually get executed; it is only parsed by mypy.
    access_token = "patFakeAccessToken"
    base_id = "appTheTestingBase"
    table_name = "tblImaginaryTable"
    record_id = "recSomeFakeRecord"
    now = "2023-01-01T00:00:00.0000Z"

    # Ensure the type signatures for pyairtable.Api don't change.
    api = pyairtable.Api(access_token)
    assert_type(api.build_url("foo", "bar"), pyairtable.utils.Url)
    assert_type(api.base(base_id), pyairtable.Base)
    assert_type(api.table(base_id, table_name), pyairtable.Table)
    assert_type(api.whoami(), T.UserAndScopesDict)

    # Ensure the type signatures for pyairtable.Base don't change.
    base = pyairtable.Base(api, base_id)
    assert_type(base.table(table_name), pyairtable.Table)
    assert_type(base.id, str)

    # Ensure the type signatures for pyairtable.Table don't change.
    table = pyairtable.Table(None, base, table_name)
    assert_type(table, pyairtable.Table)
    assert_type(table.get(record_id), T.RecordDict)
    assert_type(table.iterate(), Iterator[List[T.RecordDict]])
    assert_type(table.all(), List[T.RecordDict])
    assert_type(table.first(), Optional[T.RecordDict])
    assert_type(table.create({}), T.RecordDict)
    assert_type(table.update(record_id, {}), T.RecordDict)
    assert_type(table.delete(record_id), T.RecordDeletedDict)
    assert_type(table.batch_create([]), List[T.RecordDict])
    assert_type(table.batch_update([]), List[T.RecordDict])
    assert_type(table.batch_upsert([], []), T.UpsertResultDict)
    assert_type(table.batch_delete([]), List[T.RecordDeletedDict])

    # Ensure we can set all kinds of field values
    table.update(record_id, {"Field Name": "name"})
    table.update(record_id, {"Field Name": 1})
    table.update(record_id, {"Field Name": 1.0})
    table.update(record_id, {"Field Name": True})
    table.update(record_id, {"Field Name": None})
    table.update(record_id, {"Field Name": {"id": "usrXXX"}})
    table.update(record_id, {"Field Name": {"email": "alice@example.com"}})
    table.update(record_id, {"Field Name": ["rec1", "rec2", "rec3"]})

    # Ensure batch_upsert takes both records with and without IDs
    table.batch_upsert(
        [
            {"fields": {"Name": "Carol"}},
            {"id": "recAsdf", "fields": {"Name": "Bob"}},
            {"id": "recAsdf", "createdTime": "", "fields": {"Name": "Alice"}},
        ],
        key_fields=["Name"],
    )

    # Test type annotations for the ORM
    class Actor(orm.Model):
        name = orm.fields.SingleLineTextField("Name")
        logins = orm.fields.MultipleCollaboratorsField("Logins")
        bio = orm.fields.MultilineTextField("Bio")

    assert_type(Actor().name, str)
    assert_type(
        Actor().logins,
        L.ChangeTrackingList[Union[T.CollaboratorDict, T.CollaboratorEmailDict]],
    )
    Actor().logins.append({"id": "usr123"})
    Actor().logins.append({"email": "alice@example.com"})
    Actor().logins = [{"id": "usr123"}]
    Actor().logins = [{"email": "alice@example.com"}]

    class Movie(orm.Model):
        name = orm.fields.TextField("Name")
        rating = orm.fields.RatingField("Star Rating")
        prequels = orm.fields.LinkField["Movie"]("Prequels", "path.to.Movie")
        actors = orm.fields.LinkField("Actors", Actor)
        prequel = orm.fields.SingleLinkField["Movie"]("Prequels", orm.fields.LinkSelf)

    movie = Movie()
    assert_type(movie.name, str)
    assert_type(movie.rating, Optional[int])
    assert_type(movie.actors, L.ChangeTrackingList[Actor])
    assert_type(movie.prequels, L.ChangeTrackingList[Movie])
    assert_type(movie.prequel, Optional[Movie])
    assert_type(movie.actors[0], Actor)
    assert_type(movie.actors[0].name, str)

    class EveryField(orm.Model):
        aitext = orm.fields.AITextField("AI Generated Text")
        attachments = orm.fields.AttachmentsField("Attachments")
        autonumber = orm.fields.AutoNumberField("Autonumber")
        barcode = orm.fields.BarcodeField("Barcode")
        button = orm.fields.ButtonField("Open URL")
        checkbox = orm.fields.CheckboxField("Done")
        collaborator = orm.fields.CollaboratorField("Assignee")
        count = orm.fields.CountField("Count")
        created_by = orm.fields.CreatedByField("Created By")
        created = orm.fields.CreatedTimeField("Created")
        currency = orm.fields.CurrencyField("Dollars")
        date = orm.fields.DateField("Date")
        datetime = orm.fields.DatetimeField("DateTime")
        duration = orm.fields.DurationField("Duration (h:mm)")
        email = orm.fields.EmailField("Email")
        float = orm.fields.FloatField("Decimal 1")
        integer = orm.fields.IntegerField("Integer")
        last_modified_by = orm.fields.LastModifiedByField("Last Modified By")
        last_modified = orm.fields.LastModifiedTimeField("Last Modified")
        multi_user = orm.fields.MultipleCollaboratorsField("Watchers")
        multi_select = orm.fields.MultipleSelectField("Tags")
        number = orm.fields.NumberField("Number")
        percent = orm.fields.PercentField("Percent")
        phone = orm.fields.PhoneNumberField("Phone")
        rating = orm.fields.RatingField("Stars")
        rich_text = orm.fields.RichTextField("Notes")
        select = orm.fields.SelectField("Status")
        url = orm.fields.UrlField("URL")
        required_aitext = orm.fields.RequiredAITextField("AI Generated Text")
        required_barcode = orm.fields.RequiredBarcodeField("Barcode")
        required_collaborator = orm.fields.RequiredCollaboratorField("Assignee")
        required_count = orm.fields.RequiredCountField("Count")
        required_currency = orm.fields.RequiredCurrencyField("Dollars")
        required_date = orm.fields.RequiredDateField("Date")
        required_datetime = orm.fields.RequiredDatetimeField("DateTime")
        required_duration = orm.fields.RequiredDurationField("Duration (h:mm)")
        required_email = orm.fields.RequiredEmailField("Email")
        required_float = orm.fields.RequiredFloatField("Decimal 1")
        required_integer = orm.fields.RequiredIntegerField("Integer")
        required_number = orm.fields.RequiredNumberField("Number")
        required_percent = orm.fields.RequiredPercentField("Percent")
        required_phone = orm.fields.RequiredPhoneNumberField("Phone")
        required_rating = orm.fields.RequiredRatingField("Stars")
        required_rich_text = orm.fields.RequiredRichTextField("Notes")
        required_select = orm.fields.RequiredSelectField("Status")
        required_url = orm.fields.RequiredUrlField("URL")

    # Check the types of values returned from these fields
    # fmt: off
    record = EveryField()
    assert_type(record.aitext, Optional[T.AITextDict])
    assert_type(record.attachments, L.AttachmentsList)
    assert_type(record.attachments[0], Union[T.AttachmentDict, T.CreateAttachmentDict])
    assert_type(record.attachments.upload("", b""), None)
    assert_type(record.autonumber, int)
    assert_type(record.barcode, Optional[T.BarcodeDict])
    assert_type(record.button, T.ButtonDict)
    assert_type(record.checkbox, bool)
    assert_type(record.collaborator, Optional[Union[T.CollaboratorDict, T.CollaboratorEmailDict]])
    assert_type(record.count, Optional[int])
    assert_type(record.created_by, T.CollaboratorDict)
    assert_type(record.created, datetime.datetime)
    assert_type(record.currency, Optional[Union[int, float]])
    assert_type(record.date, Optional[datetime.date])
    assert_type(record.datetime, Optional[datetime.datetime])
    assert_type(record.duration, Optional[datetime.timedelta])
    assert_type(record.email, str)
    assert_type(record.float, Optional[float])
    assert_type(record.integer, Optional[int])
    assert_type(record.last_modified_by, Optional[T.CollaboratorDict])
    assert_type(record.last_modified, Optional[datetime.datetime])
    assert_type(record.multi_user, L.ChangeTrackingList[Union[T.CollaboratorDict, T.CollaboratorEmailDict]])
    assert_type(record.multi_user[0], Union[T.CollaboratorDict, T.CollaboratorEmailDict])
    assert_type(record.multi_select, L.ChangeTrackingList[str])
    assert_type(record.multi_select[0], str)
    assert_type(record.number, Optional[Union[int, float]])
    assert_type(record.percent, Optional[Union[int, float]])
    assert_type(record.phone, str)
    assert_type(record.rating, Optional[int])
    assert_type(record.rich_text, str)
    assert_type(record.select, Optional[str])
    assert_type(record.url, str)
    assert_type(record.required_aitext, T.AITextDict)
    assert_type(record.required_barcode, T.BarcodeDict)
    assert_type(record.required_collaborator, Union[T.CollaboratorDict, T.CollaboratorEmailDict])
    assert_type(record.required_count, int)
    assert_type(record.required_currency, Union[int, float])
    assert_type(record.required_date, datetime.date)
    assert_type(record.required_datetime, datetime.datetime)
    assert_type(record.required_duration, datetime.timedelta)
    assert_type(record.required_email, str)
    assert_type(record.required_float, float)
    assert_type(record.required_integer, int)
    assert_type(record.required_number, Union[int, float])
    assert_type(record.required_percent, Union[int, float])
    assert_type(record.required_phone, str)
    assert_type(record.required_rating, int)
    assert_type(record.required_rich_text, str)
    assert_type(record.required_select, str)
    assert_type(record.required_url, str)

    # Check the types of each field schema
    assert_type(Movie.name.field_schema(), Union[schema.SingleLineTextFieldSchema, schema.MultilineTextFieldSchema])
    assert_type(Actor.name.field_schema(), schema.SingleLineTextFieldSchema)
    assert_type(Actor.bio.field_schema(), schema.MultilineTextFieldSchema)
    assert_type(EveryField.aitext.field_schema(), schema.AITextFieldSchema)
    assert_type(EveryField.attachments.field_schema(), schema.MultipleAttachmentsFieldSchema)
    assert_type(EveryField.autonumber.field_schema(), schema.AutoNumberFieldSchema)
    assert_type(EveryField.barcode.field_schema(), schema.BarcodeFieldSchema)
    assert_type(EveryField.button.field_schema(), schema.ButtonFieldSchema)
    assert_type(EveryField.checkbox.field_schema(), schema.CheckboxFieldSchema)
    assert_type(EveryField.collaborator.field_schema(), schema.SingleCollaboratorFieldSchema)
    assert_type(EveryField.count.field_schema(), schema.CountFieldSchema)
    assert_type(EveryField.created_by.field_schema(), schema.CreatedByFieldSchema)
    assert_type(EveryField.created.field_schema(), schema.CreatedTimeFieldSchema)
    assert_type(EveryField.currency.field_schema(), schema.CurrencyFieldSchema)
    assert_type(EveryField.date.field_schema(), schema.DateFieldSchema)
    assert_type(EveryField.datetime.field_schema(), schema.DateTimeFieldSchema)
    assert_type(EveryField.duration.field_schema(), schema.DurationFieldSchema)
    assert_type(EveryField.email.field_schema(), schema.EmailFieldSchema)
    assert_type(EveryField.float.field_schema(), schema.NumberFieldSchema)
    assert_type(EveryField.integer.field_schema(), schema.NumberFieldSchema)
    assert_type(EveryField.last_modified_by.field_schema(), schema.LastModifiedByFieldSchema)
    assert_type(EveryField.last_modified.field_schema(), schema.LastModifiedTimeFieldSchema)
    assert_type(EveryField.multi_user.field_schema(), schema.MultipleCollaboratorsFieldSchema)
    assert_type(EveryField.multi_select.field_schema(), schema.MultipleSelectsFieldSchema)
    assert_type(EveryField.number.field_schema(), schema.NumberFieldSchema)
    assert_type(EveryField.percent.field_schema(), schema.PercentFieldSchema)
    assert_type(EveryField.phone.field_schema(), schema.PhoneNumberFieldSchema)
    assert_type(EveryField.rating.field_schema(), schema.RatingFieldSchema)
    assert_type(EveryField.rich_text.field_schema(), schema.RichTextFieldSchema)
    assert_type(EveryField.select.field_schema(), schema.SingleSelectFieldSchema)
    assert_type(EveryField.url.field_schema(), schema.UrlFieldSchema)
    assert_type(EveryField.required_aitext.field_schema(), schema.AITextFieldSchema)
    assert_type(EveryField.required_barcode.field_schema(), schema.BarcodeFieldSchema)
    assert_type(EveryField.required_collaborator.field_schema(), schema.SingleCollaboratorFieldSchema)
    assert_type(EveryField.required_count.field_schema(), schema.CountFieldSchema)
    assert_type(EveryField.required_currency.field_schema(), schema.CurrencyFieldSchema)
    assert_type(EveryField.required_date.field_schema(), schema.DateFieldSchema)
    assert_type(EveryField.required_datetime.field_schema(), schema.DateTimeFieldSchema)
    assert_type(EveryField.required_duration.field_schema(), schema.DurationFieldSchema)
    assert_type(EveryField.required_email.field_schema(), schema.EmailFieldSchema)
    assert_type(EveryField.required_float.field_schema(), schema.NumberFieldSchema)
    assert_type(EveryField.required_integer.field_schema(), schema.NumberFieldSchema)
    assert_type(EveryField.required_number.field_schema(), schema.NumberFieldSchema)
    assert_type(EveryField.required_percent.field_schema(), schema.PercentFieldSchema)
    assert_type(EveryField.required_phone.field_schema(), schema.PhoneNumberFieldSchema)
    assert_type(EveryField.required_rating.field_schema(), schema.RatingFieldSchema)
    assert_type(EveryField.required_rich_text.field_schema(), schema.RichTextFieldSchema)
    assert_type(EveryField.required_select.field_schema(), schema.SingleSelectFieldSchema)
    assert_type(EveryField.required_url.field_schema(), schema.UrlFieldSchema)
    assert_type(EveryField.meta.table.schema().field("Anything"), schema.FieldSchema)
    # fmt: on

    # Check that the type system allows create-style dicts in all places
    record.attachments.append({"id": "att123"})
    record.attachments.append({"url": "example.com"})
    record.attachments.append({"url": "example.com", "filename": "a.jpg"})
    record.attachments = [{"id": "att123"}]
    record.attachments = [{"url": "example.com"}]
    record.attachments = [{"url": "example.com", "filename": "a.jpg"}]
    record.collaborator = {"id": "usr123"}
    record.collaborator = {"email": "alice@example.com"}
    record.required_collaborator = {"id": "usr123"}
    record.required_collaborator = {"email": "alice@example.com"}
    record.multi_user.append({"id": "usr123"})
    record.multi_user.append({"email": "alice@example.com"})

    # Test type annotations for the formulas module
    formula = F.Formula("{Name} = 'Bob'")
    assert_type(formula & formula, F.Formula)
    assert_type(formula | formula, F.Formula)
    assert_type(~formula, F.Formula)
    assert_type(formula ^ formula, F.Formula)
    assert_type(formula & True, F.Formula)
    assert_type(formula | False, F.Formula)
    assert_type(formula ^ "literal", F.Formula)
    assert_type(F.match({"Name": "Bob"}), F.Formula)
    assert_type(F.to_formula(formula), F.Formula)
    assert_type(F.to_formula(1), F.Formula)
    assert_type(F.to_formula(True), F.Formula)
    assert_type(F.to_formula("Bob"), F.Formula)
    assert_type(F.CONCATENATE(1, 2, 3), F.FunctionCall)
