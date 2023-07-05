import datetime
import operator
import re

import pytest

from pyairtable.orm import fields as f
from pyairtable.orm.model import Model
from pyairtable.testing import (
    fake_attachment,
    fake_id,
    fake_meta,
    fake_record,
    fake_user,
)

DATE_S = "2023-01-01"
DATE_V = datetime.date(2023, 1, 1)
DATETIME_S = "2023-04-12T09:30:00.000Z"
DATETIME_V = datetime.datetime(2023, 4, 12, 9, 30, 0)


def test_field():
    class T:
        name = f.Field("Name")

    t = T()
    t.name = "x"
    assert t.name == "x"
    assert t.__dict__["_fields"]["Name"] == "x"

    with pytest.raises(AttributeError):
        del t.name


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
    ],
)
def test_repr(instance, expected):
    assert repr(instance) == expected


@pytest.mark.parametrize(
    argnames=("field_type", "default_value"),
    argvalues=[
        (f.Field, None),
        (f.CheckboxField, False),
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


# Mapping from types to a test value for that type.
TYPE_VALIDATION_TEST_VALUES = {
    **{t: t() for t in (str, bool, list, dict)},
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
        (f.TextField, str),
        (f.IntegerField, int),
        (f.RichTextField, str),
        (f.DatetimeField, datetime.datetime),
        (f.TextField, str),
        (f.CheckboxField, bool),
        (f.BarcodeField, dict),
        (f.NumberField, (int, float)),
        (f.PhoneNumberField, str),
        (f.DurationField, datetime.timedelta),
        (f.RatingField, int),
        (f.UrlField, str),
        (f.MultipleSelectField, list),
        (f.PercentField, (int, float)),
        (f.DateField, (datetime.date, datetime.datetime)),
        (f.FloatField, float),
        (f.CollaboratorField, dict),
        (f.SelectField, str),
        (f.EmailField, str),
        (f.AttachmentsField, list),
        (f.MultipleCollaboratorsField, list),
        (f.CurrencyField, (int, float)),
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
        (f.AutoNumberField, 1),
        (f.CountField, 1),
        (f.ExternalSyncSourceField, "Source"),
        (f.ButtonField, {"label": "Click me!"}),
        (f.LookupField, ["any", "values"]),
        # If a 3-tuple, we should be able to convert API -> ORM values.
        (f.CreatedByField, fake_user()),
        (f.CreatedTimeField, DATETIME_S, DATETIME_V),
        (f.LastModifiedByField, fake_user()),
        (f.LastModifiedTimeField, DATETIME_S, DATETIME_V),
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
        (f.SelectField, "any value"),
        (f.UrlField, "www.airtable.com"),
        # If a 3-tuple, we should be able to convert API -> ORM values.
        (f.DateField, DATE_S, DATE_V),
        (f.DurationField, 100.5, datetime.timedelta(seconds=100, microseconds=500000)),
        (f.DatetimeField, DATETIME_S, DATETIME_V),
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


def test_completeness():
    """
    Ensure that we test conversion of all readonly and writable fields.
    """
    assert_all_fields_tested_by(test_writable_fields, test_readonly_fields)
    assert_all_fields_tested_by(
        test_type_validation,
        exclude=f.READONLY_FIELDS | {f.LinkField},
    )


def assert_all_fields_tested_by(*test_fns, exclude=(f.Field, f.LinkField)):
    """
    Allows meta-tests that fail if any new Field classes appear in pyairtable.orm.fields
    which are not covered by one of a few basic tests. This is intended to help remind
    us as contributors to test our edge cases :)
    """

    def extract_fields(obj):
        if isinstance(obj, pytest.Mark):
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
        if isinstance(pytestmark, pytest.Mark) and pytestmark.name == "parametrize"
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


def test_list_field_with_invalid_type():
    """
    Ensure that a ListField represents a null value as an empty list.
    """

    class T(Model):
        Meta = fake_meta()
        the_field = f._ListField("Field Name", str)

    obj = T.from_record(fake_record())
    with pytest.raises(TypeError):
        obj.the_field = object()


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


def test_link_field_must_link_to_model():
    """
    Tests that a LinkField cannot link to an arbitrary type.
    """
    with pytest.raises(TypeError):
        f.LinkField("Field Name", model=dict)


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


class Dummy(Model):
    Meta = fake_meta()


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

    requests_mock.get(Person.get_table().record_url(id_a), json=rec_a)
    a = Person.from_id(id_a)

    for record in (rec_a, rec_b, rec_c):
        url_re = re.compile(
            re.escape(Person.get_table().url + "?filterByFormula=")
            + ".*"
            + record["id"]
        )
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
    person_url = Person.get_table().record_url(person_id)
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
        [re.escape(Person.get_table().url + "?filterByFormula="), *friend_ids]
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
