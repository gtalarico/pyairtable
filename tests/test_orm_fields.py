import datetime
import operator
import re
from unittest import mock

import pytest
from requests_mock import NoMockAddress

import pyairtable.exceptions
from pyairtable.formulas import OR, RECORD_ID
from pyairtable.orm import fields as f
from pyairtable.orm.lists import AttachmentsList
from pyairtable.orm.model import Model
from pyairtable.testing import (
    fake_attachment,
    fake_id,
    fake_meta,
    fake_record,
    fake_user,
)
from pyairtable.utils import datetime_to_iso_str

try:
    from pytest import Mark as _PytestMark
except ImportError:
    # older versions of pytest don't expose pytest.Mark directly
    from _pytest.mark import Mark as _PytestMark


DATE_S = "2023-01-01"
DATE_V = datetime.date(2023, 1, 1)
DATETIME_S = "2023-04-12T09:30:00.000Z"
DATETIME_V = datetime.datetime(2023, 4, 12, 9, 30, 0, tzinfo=datetime.timezone.utc)


class Dummy(Model):
    Meta = fake_meta()


def test_field():
    class T:
        name = f.Field("Name")

    t = T()
    t.name = "x"
    assert t.name == "x"
    assert t.__dict__["_fields"]["Name"] == "x"

    with pytest.raises(AttributeError):
        del t.name


def test_description():
    class T:
        name = f.Field("Name")

    T.other = f.Field("Other")

    assert T.name._description == "T.name"
    assert T.other._description == "'Other' field"


@pytest.mark.parametrize(
    "instance,expected",
    [
        (
            f.Field("Name"),
            "Field('Name', readonly=False, validate_type=True)",
        ),
        (
            f.Field("Name", readonly=True, validate_type=False),
            "Field('Name', readonly=True, validate_type=False)",
        ),
        (
            f.CollaboratorField("Collaborator"),
            "CollaboratorField('Collaborator', readonly=False, validate_type=True)",
        ),
        (
            f.LastModifiedByField("User"),
            "LastModifiedByField('User', readonly=True, validate_type=True)",
        ),
        (
            f.LookupField[dict]("Items", validate_type=False),
            "LookupField('Items', readonly=True, validate_type=False)",
        ),
        (
            f.LinkField("Records", type("TestModel", (Model,), {"Meta": fake_meta()})),
            "LinkField('Records', model=<class 'test_orm_fields.TestModel'>, validate_type=True, readonly=False, lazy=False)",
        ),
        (
            f.SingleLinkField(
                "Records", type("TestModel", (Model,), {"Meta": fake_meta()})
            ),
            "SingleLinkField('Records', model=<class 'test_orm_fields.TestModel'>, validate_type=True, readonly=False, lazy=False, raise_if_many=False)",
        ),
    ],
)
def test_repr(instance, expected):
    assert repr(instance) == expected


@pytest.mark.parametrize(
    argnames=("field_type", "default_value"),
    argvalues=[
        (f.Field, None),
        (f.CheckboxField, False),
        (f.TextField, ""),
        (f.LookupField, []),
        (f.AttachmentsField, []),
        (f.MultipleCollaboratorsField, []),
        (f.MultipleSelectField, []),
    ],
)
def test_orm_missing_values(field_type, default_value):
    """
    Test that certain field types produce the correct default value
    when there is no field value provided from Airtable.
    """

    class T(Model):
        Meta = fake_meta()
        the_field = field_type("Field Name")

    t = T()
    assert t.the_field == default_value

    t = T.from_record(fake_record({"Field Name": None}))
    assert t.the_field == default_value


# Mapping from types to a test value for that type.
TYPE_VALIDATION_TEST_VALUES = {
    str: "some value",
    bool: False,
    list: [],
    dict: {},
    int: 1,  # cannot use int() because RatingField requires value >= 1
    float: 1.0,  # cannot use float() because RatingField requires value >= 1
    datetime.date: datetime.date.today(),
    datetime.datetime: datetime.datetime.now(),
    datetime.timedelta: datetime.timedelta(seconds=1),
}


@pytest.mark.parametrize(
    "test_case",
    [
        (f.Field, tuple(TYPE_VALIDATION_TEST_VALUES)),
        (f.AttachmentsField, list),
        (f.BarcodeField, dict),
        (f.CheckboxField, bool),
        (f.CollaboratorField, dict),
        (f.CurrencyField, (int, float)),
        (f.DateField, (datetime.date, datetime.datetime)),
        (f.DatetimeField, datetime.datetime),
        (f.DurationField, datetime.timedelta),
        (f.EmailField, str),
        (f.FloatField, float),
        (f.IntegerField, int),
        (f.MultipleCollaboratorsField, list),
        (f.MultipleSelectField, list),
        (f.NumberField, (int, float)),
        (f.PercentField, (int, float)),
        (f.PhoneNumberField, str),
        (f.RatingField, int),
        (f.RichTextField, str),
        (f.SelectField, str),
        (f.TextField, str),
        (f.TextField, str),
        (f.UrlField, str),
        (f.RequiredBarcodeField, dict),
        (f.RequiredCollaboratorField, dict),
        (f.RequiredCurrencyField, (int, float)),
        (f.RequiredDateField, (datetime.date, datetime.datetime)),
        (f.RequiredDatetimeField, datetime.datetime),
        (f.RequiredDurationField, datetime.timedelta),
        (f.RequiredFloatField, float),
        (f.RequiredIntegerField, int),
        (f.RequiredNumberField, (int, float)),
        (f.RequiredPercentField, (int, float)),
        (f.RequiredRatingField, int),
        (f.RequiredSelectField, str),
        (f.RequiredEmailField, str),
        (f.RequiredPhoneNumberField, str),
        (f.RequiredRichTextField, str),
        (f.RequiredTextField, str),
        (f.RequiredUrlField, str),
    ],
    ids=operator.itemgetter(0),
)
def test_type_validation(test_case):
    """
    Test that attempting to assign the wrong type of value to a field
    will throw TypeError, but the right kind of value will work.
    """
    field_type, accepted_types = test_case
    if isinstance(accepted_types, type):
        accepted_types = [accepted_types]

    class T:
        the_field = field_type("Field Name")
        unvalidated_field = field_type("Unvalidated", validate_type=False)

    t = T()

    for testing_type, test_value in TYPE_VALIDATION_TEST_VALUES.items():
        # This statement should not raise an exception, no matter what. Caveat emptor.
        t.unvalidated_field = test_value

        if testing_type in accepted_types:
            t.the_field = test_value
        else:
            with pytest.raises(TypeError):
                t.the_field = test_value
                pytest.fail(
                    f"{field_type.__name__} = {test_value!r} {testing_type} did not raise TypeError"
                )


def test_type_validation_LinkField():
    """
    Test that a link field will reject models of the wrong class.
    """

    class A(Model):
        Meta = fake_meta()

    class B(Model):
        Meta = fake_meta()

    class Container(Model):
        Meta = fake_meta()
        linked = f.LinkField("Linked", model=A)

    a1 = A.from_record(fake_record())
    a2 = A.from_record(fake_record())
    a3 = A.from_record(fake_record())
    b1 = B.from_record(fake_record())
    b2 = B.from_record(fake_record())
    b3 = B.from_record(fake_record())

    record = Container()
    assert record.linked == []

    record.linked.append(a1)
    record.linked.append(a2)
    assert record.to_record()["fields"]["Linked"] == [a1.id, a2.id]

    record.linked = [a1, a2, a3]
    assert record.to_record()["fields"]["Linked"] == [a1.id, a2.id, a3.id]

    # We can validate the type of each object during assignment
    with pytest.raises(TypeError):
        record.linked = [b1, b2, b3]

    # We can't (easily) stop an implementer from appending the wrong type
    # to the end of the list, but we can catch it during to_record().
    record.linked.append(b1)
    with pytest.raises(TypeError):
        record.to_record()


@pytest.mark.parametrize(
    argnames="test_case",
    argvalues=[
        # If a 2-tuple, the API and ORM values should be identical.
        (f.AITextField, {"state": "empty", "isStale": True, "value": None}),
        (f.AutoNumberField, 1),
        (f.CountField, 1),
        (f.ExternalSyncSourceField, "Source"),
        (f.ButtonField, {"label": "Click me!"}),
        (f.LookupField, ["any", "values"]),
        (f.CreatedByField, fake_user()),
        (f.LastModifiedByField, fake_user()),
        (f.ManualSortField, "fcca"),
        # If a 3-tuple, we should be able to convert API -> ORM values.
        (f.CreatedTimeField, DATETIME_S, DATETIME_V),
        (f.LastModifiedTimeField, DATETIME_S, DATETIME_V),
        # We also want to test the not-null versions of these fields
        (f.RequiredAITextField, {"state": "empty", "isStale": True, "value": None}),
        (f.RequiredCountField, 1),
    ],
    ids=operator.itemgetter(0),
)
def test_readonly_fields(test_case):
    """
    Test that a readonly field cannot be overwritten.
    """
    if len(test_case) == 2:
        field_type, api_value = test_case
        orm_value = api_value
    else:
        field_type, api_value, orm_value = test_case

    class T(Model):
        Meta = fake_meta()
        the_field = field_type("Field Name")

    assert orm_value == T.the_field.to_internal_value(api_value)
    assert api_value == T.the_field.to_record_value(orm_value)

    t = T.from_record(fake_record({"Field Name": api_value}))
    assert t.the_field == orm_value
    with pytest.raises(AttributeError):
        t.the_field = orm_value


@pytest.mark.parametrize(
    argnames="test_case",
    argvalues=[
        # If a 2-tuple, the API and ORM values should be identical.
        (f.Field, object()),  # accepts any value, but Airtable API *will* complain
        (f.TextField, "name"),
        (f.EmailField, "x@y.com"),
        (f.NumberField, 1),
        (f.NumberField, 1.5),
        (f.IntegerField, 1),
        (f.FloatField, 1.5),
        (f.RatingField, 1),
        (f.CurrencyField, 1.05),
        (f.CheckboxField, True),
        (f.CollaboratorField, {"id": "usrFakeUserId", "email": "x@y.com"}),
        (f.AttachmentsField, [fake_attachment(), fake_attachment()]),
        (f.MultipleSelectField, ["any", "values"]),
        (f.MultipleCollaboratorsField, [fake_user(), fake_user()]),
        (f.BarcodeField, {"type": "upce", "text": "084114125538"}),
        (f.PercentField, 0.5),
        (f.PhoneNumberField, "+49 40-349180"),
        (f.RichTextField, "Check out [Airtable](www.airtable.com)"),
        (f.SelectField, ""),
        (f.SelectField, "any value"),
        (f.UrlField, "www.airtable.com"),
        (f.RequiredNumberField, 1),
        (f.RequiredNumberField, 1.5),
        (f.RequiredIntegerField, 1),
        (f.RequiredFloatField, 1.5),
        (f.RequiredRatingField, 1),
        (f.RequiredCurrencyField, 1.05),
        (f.RequiredCollaboratorField, {"id": "usrFakeUserId", "email": "x@y.com"}),
        (f.RequiredBarcodeField, {"type": "upce", "text": "084114125538"}),
        (f.RequiredPercentField, 0.5),
        (f.RequiredSelectField, "any value"),
        (f.RequiredEmailField, "any value"),
        (f.RequiredPhoneNumberField, "any value"),
        (f.RequiredRichTextField, "any value"),
        (f.RequiredTextField, "any value"),
        (f.RequiredUrlField, "any value"),
        # If a 3-tuple, we should be able to convert API -> ORM values.
        (f.DateField, DATE_S, DATE_V),
        (f.DatetimeField, DATETIME_S, DATETIME_V),
        (f.DurationField, 100.5, datetime.timedelta(seconds=100, microseconds=500000)),
        (f.RequiredDateField, DATE_S, DATE_V),
        (f.RequiredDatetimeField, DATETIME_S, DATETIME_V),
        (f.RequiredDurationField, 100, datetime.timedelta(seconds=100)),
    ],
    ids=operator.itemgetter(0),
)
def test_writable_fields(test_case):
    """
    Test that the ORM does not modify values that can be persisted as-is.
    """
    if len(test_case) == 2:
        field_type, api_value = test_case
        orm_value = api_value
    else:
        field_type, api_value, orm_value = test_case

    class T(Model):
        Meta = fake_meta()
        the_field = field_type("Field Name")

    assert orm_value == T.the_field.to_internal_value(api_value)
    assert api_value == T.the_field.to_record_value(orm_value)

    new_obj = T()
    new_obj.the_field = orm_value
    assert new_obj.to_record()["fields"] == {"Field Name": api_value}

    from_init = T(the_field=orm_value)
    assert from_init.the_field == orm_value

    existing_obj = T.from_record(fake_record({"Field Name": api_value}))
    assert existing_obj.the_field == orm_value


@pytest.mark.parametrize(
    "field_type",
    [
        f.Field,
        f.AITextField,
        f.AttachmentsField,
        f.BarcodeField,
        f.CheckboxField,
        f.CollaboratorField,
        f.CountField,
        f.CurrencyField,
        f.DateField,
        f.DatetimeField,
        f.DurationField,
        f.EmailField,
        f.ExternalSyncSourceField,
        f.FloatField,
        f.IntegerField,
        f.LastModifiedByField,
        f.LastModifiedTimeField,
        f.LookupField,
        f.ManualSortField,
        f.MultipleCollaboratorsField,
        f.MultipleSelectField,
        f.NumberField,
        f.NumberField,
        f.PercentField,
        f.PhoneNumberField,
        f.RatingField,
        f.RichTextField,
        f.SelectField,
        f.TextField,
        f.UrlField,
    ],
)
def test_accepts_null(field_type):
    """
    Test field types that allow null values from Airtable.
    """

    class T(Model):
        Meta = fake_meta()
        the_field = field_type("Field Name")

    obj = T()
    assert not obj.the_field


@pytest.mark.parametrize(
    "field_type",
    [
        f.AutoNumberField,
        f.ButtonField,
        f.CreatedByField,
        f.CreatedTimeField,
        f.RequiredAITextField,
        f.RequiredBarcodeField,
        f.RequiredCollaboratorField,
        f.RequiredCountField,
        f.RequiredCurrencyField,
        f.RequiredDateField,
        f.RequiredDatetimeField,
        f.RequiredDurationField,
        f.RequiredEmailField,
        f.RequiredFloatField,
        f.RequiredIntegerField,
        f.RequiredNumberField,
        f.RequiredPercentField,
        f.RequiredPhoneNumberField,
        f.RequiredRatingField,
        f.RequiredRichTextField,
        f.RequiredSelectField,
        f.RequiredTextField,
        f.RequiredUrlField,
    ],
)
def test_rejects_null(field_type):
    """
    Test field types that do not allow null values from Airtable.
    """

    class T(Model):
        Meta = fake_meta()
        the_field = field_type("Field Name")

    obj = T()
    with pytest.raises(pyairtable.exceptions.MissingValueError):
        obj.the_field
    with pytest.raises(pyairtable.exceptions.MissingValueError):
        obj.the_field = None
    with pytest.raises(pyairtable.exceptions.MissingValueError):
        T(the_field=None)


def test_completeness():
    """
    Ensure that we test conversion of all readonly and writable fields.
    """
    assert_all_fields_tested_by(
        test_writable_fields,
        test_readonly_fields,
        exclude=(f.LinkField, f.SingleLinkField),
    )
    assert_all_fields_tested_by(
        test_type_validation,
        exclude=f.READONLY_FIELDS | {f.LinkField, f.SingleLinkField},
    )
    assert_all_fields_tested_by(
        test_accepts_null,
        test_rejects_null,
        exclude={f.LinkField, f.SingleLinkField},
    )


def assert_all_fields_tested_by(*test_fns, exclude=()):
    """
    Allows meta-tests that fail if any new Field classes appear in pyairtable.orm.fields
    which are not covered by one of a few basic tests. This is intended to help remind
    us as contributors to test our edge cases :)
    """

    def extract_fields(obj):
        if isinstance(obj, _PytestMark):
            yield from [*extract_fields(obj.args), *extract_fields(obj.kwargs)]
        elif isinstance(obj, str):
            pass
        elif isinstance(obj, dict):
            yield from extract_fields(list(obj.values()))
        elif isinstance(obj, type):
            if issubclass(obj, f.Field):
                yield obj
        elif hasattr(obj, "__iter__"):
            for item in obj:
                yield from extract_fields(item)

    tested_field_classes = {
        field_class
        for test_function in test_fns
        for pytestmark in getattr(test_function, "pytestmark", [])
        if isinstance(pytestmark, _PytestMark) and pytestmark.name == "parametrize"
        for field_class in extract_fields(pytestmark)
        if field_class not in exclude
    }

    missing = [
        field_class_name
        for field_class_name, field_class in vars(f).items()
        if field_class_name.endswith("Field")
        and isinstance(field_class, type)
        and field_class not in tested_field_classes
        and field_class not in exclude
        and not field_class.__name__.startswith("_")
    ]

    if missing:
        test_names = sorted(fn.__name__ for fn in test_fns)
        fail_names = "\n".join(f"- {name}" for name in missing)
        pytest.fail(f"Some fields were not tested by {test_names}:\n{fail_names}")


def test_invalid_kwarg():
    """
    Ensure we raise AttributeError if an invalid kwarg is passed to the constructor.
    """

    class T(Model):
        Meta = fake_meta()
        the_field = f.TextField("Field Name")

    assert T(the_field="whatever").the_field == "whatever"
    with pytest.raises(AttributeError):
        T(foo="bar")


def test_list_field_with_none():
    """
    Ensure that a ListField represents a null value as an empty list.
    """

    class T(Model):
        Meta = fake_meta()
        the_field = f._ListField("Fld", str)

    assert T.from_record(fake_record()).the_field == []
    assert T.from_record(fake_record(Fld=None)).the_field == []


@pytest.mark.parametrize(
    "field_class,invalid_value",
    [
        (f._ListField, object()),
        (f.AttachmentsField, [1, 2, 3]),
        (f.MultipleCollaboratorsField, [1, 2, 3]),
        (f.MultipleSelectField, [{"complex": "type"}]),
    ],
)
def test_list_field_with_invalid_type(field_class, invalid_value):
    """
    Ensure that a ListField raises TypeError when given a non-list,
    or a list of objects that don't match `contains_type`.
    """

    class T(Model):
        Meta = fake_meta()
        the_field = field_class("Field Name", str)

    obj = T.from_record(fake_record())
    with pytest.raises(TypeError):
        obj.the_field = invalid_value


def test_list_field_with_string():
    """
    If we pass a string to a list field, it should not be turned
    into a list of single-character strings; it should be an error.
    """

    class T:
        items = f._ListField("Items", str)

    t = T()
    with pytest.raises(TypeError):
        t.items = "hello!"


@pytest.mark.parametrize("cls", (f.LinkField, f.SingleLinkField))
def test_link_field_must_link_to_model(cls):
    """
    Tests that a LinkField cannot link to an arbitrary type.
    """
    with pytest.raises(TypeError):
        cls("Field Name", model=dict)


def test_link_field():
    """
    Test basic interactions and type checking for LinkField.
    """

    class Book(Model):
        Meta = fake_meta()

    class Author(Model):
        Meta = fake_meta()
        books = f.LinkField("Books", model=Book)

    collection = [Book(), Book(), Book()]
    author = Author()
    author.books = collection
    assert author.books == collection

    with pytest.raises(TypeError):
        author.books = Book()

    with pytest.raises(TypeError):
        author.books = [1, 2, 3]

    with pytest.raises(TypeError):
        author.books = -1


def test_link_field__linked_model():
    """
    Test the various ways of specifying a linked model for the LinkField.
    """

    class HasLinks(Model):
        Meta = fake_meta()
        # If the other model class is available, you can link to it directly
        explicit_link = f.LinkField("explicit", Dummy)
        # You can pass a fully qualified path.to.module.Class
        indirect_link = f.LinkField("indirect", "test_orm_fields.Dummy")
        # If there's no module, just a class, we assume it's in the same module
        neighbor_link = f.LinkField("neighbor", "Dummy")
        # Sentinel value LinkSelf means "link to the same model"
        circular_link = f.LinkField("circular", f.LinkSelf)

    assert HasLinks.explicit_link.linked_model is Dummy
    assert HasLinks.indirect_link.linked_model is Dummy
    assert HasLinks.neighbor_link.linked_model is Dummy
    assert HasLinks.circular_link.linked_model is HasLinks

    # While it is technically possible to add fields to a Model class after creation,
    # those fields won't get __set_name__ called, which means they won't have a
    # reference to their own Model class. This means...

    # ...that LinkField(model=f.LinkSelf) won't work:
    HasLinks.invalid_circular_link = f.LinkField("Invalid", f.LinkSelf)
    with pytest.raises(RuntimeError):
        HasLinks.invalid_circular_link.linked_model

    # ...and LinkField(model="Class") without the module path won't work:
    HasLinks.invalid_neighbor_link = f.LinkField("Invalid", "Dummy")
    with pytest.raises(RuntimeError):
        HasLinks.invalid_neighbor_link.linked_model


class Person(Model):
    Meta = fake_meta()
    friends = f.LinkField("Friends", f.LinkSelf, lazy=False)


def test_link_field__cycle(requests_mock):
    """
    Test that cyclical relationships like A -> B -> C -> A don't cause infinite recursion.
    """

    id_a = fake_id("rec", "A")
    id_b = fake_id("rec", "B")
    id_c = fake_id("rec", "C")
    rec_a = {"id": id_a, "createdTime": DATETIME_S, "fields": {"Friends": [id_b]}}
    rec_b = {"id": id_b, "createdTime": DATETIME_S, "fields": {"Friends": [id_c]}}
    rec_c = {"id": id_c, "createdTime": DATETIME_S, "fields": {"Friends": [id_a]}}

    requests_mock.get(Person.meta.table.urls.record(id_a), json=rec_a)
    a = Person.from_id(id_a)

    url = Person.meta.table.urls.records
    for record in (rec_a, rec_b, rec_c):
        url_re = re.compile(re.escape(f"{url}?filterByFormula=") + ".*" + record["id"])
        requests_mock.get(url_re, json={"records": [record]})

    assert a.friends[0].id == id_b
    assert a.friends[0].friends[0].id == id_c
    assert a.friends[0].friends[0].friends[0].id == id_a


def test_link_field__load_many(requests_mock):
    """
    Tests that a LinkField which returns several IDs will minimize the number
    of API calls it makes in order to fetch data.
    """

    person_id = fake_id("rec", "A")
    person_url = Person.meta.table.urls.record(person_id)
    friend_ids = [fake_id("rec", c) for c in "123456789ABCDEF"]

    person_json = {
        "id": person_id,
        "createdTime": DATETIME_S,
        "fields": {"Friends": friend_ids},
    }
    friends_json = [
        {"id": record_id, "createdTime": DATETIME_S, "fields": {"Name": record_id[-1]}}
        for record_id in friend_ids
    ]

    # This retrieves a record; we test this behavior elsewhere, no need to check values
    requests_mock.get(person_url, json=person_json)
    person = Person.from_id(person_id)

    # Here we test that calling `person.friends` retrieves records in bulk,
    # instead of calling `.fetch()` on every record individually.
    # The mocked URL specifically includes every record ID in our test set,
    # to ensure the library isn't somehow dropping records from its query.
    url_regex = ".*".join(
        [re.escape(Person.meta.table.urls.records + "?filterByFormula="), *friend_ids]
    )
    mock_list = requests_mock.get(
        re.compile(url_regex),
        [
            {"json": {"records": friends_json[:10], "offset": "offset1"}},
            {"json": {"records": friends_json[10:]}},
        ],
    )
    assert person.friends
    assert mock_list.call_count == 2
    assert len(person.friends) == len(friend_ids)
    assert [friend.id for friend in person.friends] == friend_ids
    # Make sure we didn't keep calling the API on every `person.friends`
    assert mock_list.call_count == 2


@pytest.mark.parametrize(
    "mutation",
    (
        "author.books = [book]",
        "author.books.append(book)",
        "author.books[0] = book",
        "author.books.insert(0, book)",
        "author.books[0:1] = []",
        "author.books.pop(0)",
        "del author.books[0]",
        "author.books.remove(author.books[0])",
        "author.books.clear()",
        "author.books.extend([book])",
    ),
)
def test_link_field__save(requests_mock, mutation):
    """
    Test that we correctly detect changes to linked fields and save them.
    """

    class Book(Model):
        Meta = fake_meta()

    class Author(Model):
        Meta = fake_meta()
        books = f.LinkField("Books", model=Book)

    b1 = Book.from_record(fake_record())
    b2 = Book.from_record(fake_record())
    author = Author.from_record(fake_record({"Books": [b1.id]}))

    def _cb(request, context):
        return {
            "id": author.id,
            "createdTime": datetime_to_iso_str(author.created_time),
            "fields": request.json()["fields"],
        }

    requests_mock.get(
        Book.meta.table.urls.records,
        json={"records": [b1.to_record(), b2.to_record()]},
    )
    m = requests_mock.patch(Author.meta.table.urls.record(author.id), json=_cb)
    exec(mutation, {}, {"author": author, "book": b2})
    assert author._changed["Books"]
    author.save()
    assert m.call_count == 1
    assert "Books" in m.last_request.json()["fields"]


def test_single_link_field():
    class Author(Model):
        Meta = fake_meta()
        name = f.TextField("Name")

    class Book(Model):
        Meta = fake_meta()
        author = f.SingleLinkField("Author", Author, lazy=True)

    assert Book.author.linked_model is Author

    book = Book()
    assert book.author is None

    with pytest.raises(TypeError):
        book.author = [Author()]

    with pytest.raises(TypeError):
        book.author = []

    alice = Author.from_record(fake_record(Name="Alice"))
    book.author = alice

    with mock.patch("pyairtable.Table.get", return_value=alice.to_record()) as m:
        book.author.fetch()
        m.assert_called_once_with(alice.id)

    assert book.author.id == alice.id
    assert book.author.name == "Alice"

    book.author = (bob := Author(name="Bob"))
    assert not book.author.exists()
    assert book.author.name == "Bob"

    with mock.patch("pyairtable.Table.create", return_value=fake_record()) as m:
        book.author.save()
        m.assert_called_once_with({"Name": "Bob"}, typecast=True)

    with mock.patch("pyairtable.Table.create", return_value=fake_record()) as m:
        book.save()
        m.assert_called_once_with({"Author": [bob.id]}, typecast=True)

    with mock.patch("pyairtable.Table.update", return_value=book.to_record()) as m:
        book.author = None
        book.save()
        m.assert_called_once_with(book.id, {"Author": None}, typecast=True)


def test_single_link_field__multiple_values():
    """
    Test the behavior of SingleLinkField when the Airtable API
    returns multiple values.
    """

    class Author(Model):
        Meta = fake_meta()
        name = f.TextField("Name")

    class Book(Model):
        Meta = fake_meta()
        author = f.SingleLinkField("Author", Author)

    records = [fake_record(Name=f"Author {n+1}") for n in range(3)]
    a1, a2, a3 = [r["id"] for r in records]

    # if Airtable sends back multiple IDs, we'll only retrieve the first one.
    book = Book.from_record(fake_record(Author=[a1, a2, a3]))
    with mock.patch("pyairtable.Table.all", return_value=records) as m:
        book.author
        m.assert_called_once_with(formula=OR(RECORD_ID().eq(records[0]["id"])))

    assert book.author.id == a1
    assert book.author.name == "Author 1"
    assert book._fields["Author"][1:] == [a2, a3]  # not converted to models

    # if book.author.__set__ not called, the entire list will be sent back to the API
    with mock.patch("pyairtable.Table.update", return_value=book.to_record()) as m:
        book.save(force=True)
        m.assert_called_once_with(book.id, {"Author": [a1, a2, a3]}, typecast=True)

    # if we modify the field value, it will drop items 2-N
    book.author = Author.from_record(fake_record())
    with mock.patch("pyairtable.Table.update", return_value=book.to_record()) as m:
        book.save()
        m.assert_called_once_with(book.id, {"Author": [book.author.id]}, typecast=True)


def test_single_link_field__raise_if_many():
    """
    Test that passing raise_if_many=True to SingleLinkField will cause an exception
    to be raised if (1) the field receives multiple values and (2) is accessed.
    """

    class Author(Model):
        Meta = fake_meta()
        name = f.TextField("Name")

    class Book(Model):
        Meta = fake_meta()
        author = f.SingleLinkField("Author", Author, raise_if_many=True)

    book = Book.from_record(fake_record(Author=[fake_id(), fake_id()]))
    with pytest.raises(pyairtable.exceptions.MultipleValuesError):
        book.author


@pytest.mark.parametrize("field_type", (f.LinkField, f.SingleLinkField))
def test_link_field__populate(field_type, requests_mock):
    """
    Test that implementers can use Model.link_field.populate(instance) to control
    whether loading happens lazy or non-lazy at runtime.
    """

    class Linked(Model):
        Meta = fake_meta()
        name = f.TextField("Name")

    class T(Model):
        Meta = fake_meta()
        link = field_type("Link", Linked)

    links = [fake_record(id=n, Name=f"link{n}") for n in range(1, 4)]
    link_ids = [link["id"] for link in links]
    obj = T.from_record(fake_record(Link=link_ids[:]))
    assert obj._fields.get("Link") == link_ids
    assert obj._fields.get("Link") is not link_ids

    # calling the record directly will attempt network traffic
    with pytest.raises(NoMockAddress):
        obj.link

    # on a non-lazy field, we can still call .populate() to load it lazily
    T.link.populate(obj, lazy=True)

    if field_type is f.SingleLinkField:
        assert isinstance(obj.link, Linked)
        assert obj.link.id == links[0]["id"]
        assert obj.link.name == ""
    else:
        assert isinstance(obj.link[0], Linked)
        assert link_ids == [link.id for link in obj.link]
        assert all(link.name == "" for link in obj.link)

    # calling .populate() on the wrong model raises an exception
    with pytest.raises(RuntimeError):
        T.link.populate(Linked())


def test_lookup_field():
    class T:
        items = f.LookupField("Items")

    lookup_from_airtable = ["Item 1", "Item 2", "Item 3"]
    rv_list = T.items.to_internal_value(lookup_from_airtable)
    rv_json = T.items.to_record_value(rv_list)
    assert rv_json == lookup_from_airtable
    assert isinstance(rv_list, list)
    assert rv_list[0] == "Item 1" and rv_list[1] == "Item 2" and rv_list[2] == "Item 3"

    class T:
        events = f.LookupField("Event times")

    lookup_from_airtable = [
        "2000-01-02T03:04:05.000Z",
        "2000-02-02T03:04:05.000Z",
        "2000-03-02T03:04:05.000Z",
    ]
    rv_to_internal = T.events.to_internal_value(lookup_from_airtable)
    rv_to_record = T.events.to_record_value(rv_to_internal)
    assert rv_to_record == lookup_from_airtable
    assert isinstance(rv_to_internal, list)
    assert (
        rv_to_internal[0] == "2000-01-02T03:04:05.000Z"
        and rv_to_internal[1] == "2000-02-02T03:04:05.000Z"
        and rv_to_internal[2] == "2000-03-02T03:04:05.000Z"
    )


def test_rating_field():
    """
    Test that a RatingField does not accept floats or values below 1.
    """

    class T:
        rating = f.RatingField("Rating")

    T().rating = 1

    with pytest.raises(TypeError):
        T().rating = 0.5

    with pytest.raises(ValueError):
        T().rating = 0


def test_datetime_timezones(requests_mock):
    """
    Test that DatetimeField handles time zones properly.
    """

    class M(Model):
        Meta = fake_meta()
        dt = f.DatetimeField("dt")

    obj = M.from_record(fake_record(dt="2024-02-29T12:34:56Z"))

    def patch_callback(request, context):
        return {
            "id": obj.id,
            "createdTime": datetime_to_iso_str(obj.created_time),
            "fields": request.json()["fields"],
        }

    m = requests_mock.patch(M.meta.table.urls.record(obj.id), json=patch_callback)

    # Test that we parse the "Z" into UTC correctly
    assert obj.dt.date() == datetime.date(2024, 2, 29)
    assert obj.dt.tzinfo is datetime.timezone.utc
    obj.save(force=True)
    assert m.last_request.json()["fields"]["dt"] == "2024-02-29T12:34:56.000Z"

    # Test that we can set a UTC timezone and it will be saved as-is.
    obj.dt = datetime.datetime(2024, 3, 1, 11, 22, 33, tzinfo=datetime.timezone.utc)
    obj.save()
    assert m.last_request.json()["fields"]["dt"] == "2024-03-01T11:22:33.000Z"

    # Test that we can set a local timezone and it will be sent to Airtable.
    pacific = datetime.timezone(datetime.timedelta(hours=-8))
    obj.dt = datetime.datetime(2024, 3, 1, 11, 22, 33, tzinfo=pacific)
    obj.save()
    assert m.last_request.json()["fields"]["dt"] == "2024-03-01T11:22:33.000-08:00"

    # Test that a timezone-unaware datetime is passed as-is to Airtable.
    # This behavior will vary depending on how the field is configured.
    # See https://airtable.com/developers/web/api/field-model#dateandtime
    obj.dt = datetime.datetime(2024, 3, 1, 11, 22, 33)
    obj.save()
    assert m.last_request.json()["fields"]["dt"] == "2024-03-01T11:22:33.000"


@pytest.mark.parametrize(
    "fields,expected",
    [
        ({}, None),
        ({"Field": None}, None),
        ({"Field": ""}, ""),
        ({"Field": "xyz"}, "xyz"),
    ],
)
def test_select_field(fields, expected):
    """
    Test that select field distinguishes between empty string and None.
    """

    class T(Model):
        Meta = fake_meta()
        the_field = f.SelectField("Field")

    obj = T.from_record(fake_record(**fields))
    assert obj.the_field == expected

    with mock.patch("pyairtable.Table.update", return_value=obj.to_record()) as m:
        obj.save(force=True)
        m.assert_called_once_with(obj.id, fields, typecast=True)


@pytest.mark.parametrize(
    "class_kwargs",
    [
        {"contains_type": 1},
        {"list_class": 1},
        {"list_class": dict},
    ],
)
def test_invalid_list_class_params(class_kwargs):
    """
    Test that certain parameters to ListField are invalid.
    """

    with pytest.raises(TypeError):

        class ListFieldSubclass(f._ListField, **class_kwargs):
            pass


@mock.patch("pyairtable.Table.create")
def test_attachments__set(mock_create):
    """
    Test that AttachmentsField can be set with a list of AttachmentDict,
    and the value will be coerced to an AttachmentsList.
    """
    mock_create.return_value = {
        "id": fake_id(),
        "createdTime": DATETIME_S,
        "fields": {
            "Attachments": [
                {
                    "id": fake_id("att"),
                    "url": "https://example.com",
                    "filename": "a.jpg",
                }
            ]
        },
    }

    class T(Model):
        Meta = fake_meta()
        attachments = f.AttachmentsField("Attachments")

    obj = T()
    assert obj.attachments == []
    assert isinstance(obj.attachments, AttachmentsList)

    obj.attachments = [{"url": "https://example.com"}]
    assert isinstance(obj.attachments, AttachmentsList)

    obj.save()
    assert isinstance(obj.attachments, AttachmentsList)
    assert obj.attachments[0]["url"] == "https://example.com"


def test_attachments__set_invalid_type():
    class T(Model):
        Meta = fake_meta()
        attachments = f.AttachmentsField("Attachments")

    with pytest.raises(TypeError):
        T().attachments = [1, 2, 3]
