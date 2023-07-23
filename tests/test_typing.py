"""
Tests that pyairtable.api functions/methods return appropriately typed responses.
"""
import datetime
from typing import TYPE_CHECKING, Iterator, List, Optional, Union

from typing_extensions import assert_type

import pyairtable
import pyairtable.api.types as T
from pyairtable import orm

if TYPE_CHECKING:
    # This section does not actually get executed; it is only parsed by mypy.
    access_token = "patFakeAccessToken"
    base_id = "appTheTestingBase"
    table_name = "tblImaginaryTable"
    record_id = "recSomeFakeRecord"
    now = "2023-01-01T00:00:00.0000Z"

    # Ensure the type signatures for pyairtable.Api don't change.
    api = pyairtable.Api(access_token)
    assert_type(api.build_url("foo", "bar"), str)
    assert_type(api.base(base_id), pyairtable.Base)
    assert_type(api.table(base_id, table_name), pyairtable.Table)
    assert_type(api.whoami(), T.UserAndScopesDict)

    # Ensure the type signatures for pyairtable.Base don't change.
    base = pyairtable.Base(api, base_id)
    assert_type(base.table(table_name), pyairtable.Table)
    assert_type(base.url, str)

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

    # Test type annotations for the ORM
    class Actor(orm.Model):
        name = orm.fields.TextField("Name")
        logins = orm.fields.MultipleCollaboratorsField("Logins")

    assert_type(Actor().name, Optional[str])
    assert_type(Actor().logins, List[T.CollaboratorDict])

    class Movie(orm.Model):
        name = orm.fields.TextField("Name")
        rating = orm.fields.RatingField("Star Rating")
        prequels = orm.fields.LinkField["Movie"]("Prequels", "path.to.Movie")
        actors = orm.fields.LinkField("Actors", Actor)

    movie = Movie()
    assert_type(movie.name, Optional[str])
    assert_type(movie.rating, Optional[int])
    assert_type(movie.actors, List[Actor])
    assert_type(movie.prequels, List[Movie])
    assert_type(movie.actors[0].name, Optional[str])

    class EveryField(orm.Model):
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

    record = EveryField()
    assert_type(record.attachments, List[T.AttachmentDict])
    assert_type(record.autonumber, Optional[int])
    assert_type(record.barcode, Optional[T.BarcodeDict])
    assert_type(record.button, Optional[T.ButtonDict])
    assert_type(record.checkbox, Optional[bool])
    assert_type(record.collaborator, Optional[T.CollaboratorDict])
    assert_type(record.count, Optional[int])
    assert_type(record.created_by, Optional[T.CollaboratorDict])
    assert_type(record.created, Optional[datetime.datetime])
    assert_type(record.currency, Optional[Union[int, float]])
    assert_type(record.date, Optional[datetime.date])
    assert_type(record.datetime, Optional[datetime.datetime])
    assert_type(record.duration, Optional[datetime.timedelta])
    assert_type(record.email, Optional[str])
    assert_type(record.float, Optional[float])
    assert_type(record.integer, Optional[int])
    assert_type(record.last_modified_by, Optional[T.CollaboratorDict])
    assert_type(record.last_modified, Optional[datetime.datetime])
    assert_type(record.multi_user, List[T.CollaboratorDict])
    assert_type(record.multi_select, List[str])
    assert_type(record.number, Optional[Union[int, float]])
    assert_type(record.percent, Optional[Union[int, float]])
    assert_type(record.phone, Optional[str])
    assert_type(record.rating, Optional[int])
    assert_type(record.rich_text, Optional[str])
    assert_type(record.select, Optional[str])
    assert_type(record.url, Optional[str])
