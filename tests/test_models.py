import pytest

from pyairtable.models._base import (
    AirtableModel,
    SerializableModel,
    update_forward_refs,
)


@pytest.fixture
def raw_data():
    return {"foo": 1, "bar": 2, "baz": 3}


@pytest.fixture
def create_instance(api, raw_data):
    def _creates_instance(**kwargs):
        class Subclass(SerializableModel, **kwargs):
            foo: int
            bar: int
            baz: int

        return Subclass.from_api(api, "https://www.example.com", raw_data)

    return _creates_instance


def test_raw(raw_data):
    """
    Test that AirtableModel.parse_obj saves the raw value, so that developers
    can access the exact payload we received from the API. This is mostly
    in case Airtable adds new things to webhooks or webhook payloads in the future.
    """
    obj = AirtableModel.parse_obj(raw_data)
    assert not hasattr(obj, "foo")
    assert not hasattr(obj, "bar")
    assert obj._raw == raw_data


def test_from_api(raw_data):
    """
    Test that SerializableModel.from_api persists its parameters correctly.
    """
    url = "https://www.example.com"
    obj = SerializableModel.from_api("api", url, raw_data)
    assert obj._api == "api"
    assert obj._url == url
    assert obj._raw == raw_data


def test_save(requests_mock, create_instance):
    obj = create_instance()
    obj.foo *= 2
    obj.bar *= 3
    expected_patch = {"foo": 2, "bar": 6, "baz": 3}
    returned_patch = {"foo": -1, "bar": -2, "baz": -3}
    m = requests_mock.patch(obj._url, json=returned_patch)
    obj.save()
    assert m.call_count == 1
    assert m.request_history[0].json() == expected_patch
    assert obj.foo == returned_patch["foo"]
    assert obj.bar == returned_patch["bar"]
    assert obj.baz == returned_patch["baz"]


def test_save_not_allowed(create_instance):
    obj = create_instance(allow_update=False)
    with pytest.raises(NotImplementedError):
        obj.save()


def test_delete(requests_mock, create_instance):
    obj = create_instance()
    m = requests_mock.delete(obj._url)
    obj.delete()
    assert m.call_count == 1
    assert obj.deleted
    with pytest.raises(RuntimeError):
        obj.save()


def test_delete_not_allowed(create_instance):
    obj = create_instance(allow_delete=False)
    with pytest.raises(NotImplementedError):
        obj.delete()


def test_writable(create_instance):
    obj = create_instance(writable=["foo"])
    obj.foo = 0
    with pytest.raises(AttributeError):
        obj.bar = 0

    # Test that an empty list to writable= is the same as "nothing is writable"
    obj = create_instance(writable=[])
    for attr in ("foo", "bar", "baz"):
        with pytest.raises(AttributeError):
            setattr(obj, attr, 0)


def test_readonly(create_instance):
    obj = create_instance(readonly=["baz"])
    obj.foo = 0
    obj.bar = 0
    with pytest.raises(AttributeError):
        obj.baz = 0


def test_writable_and_readonly(create_instance):
    with pytest.raises(ValueError):
        create_instance(writable=["foo"], readonly=["bar"])


def test_update_forward_refs():
    """
    Test that update_forward_refs does not get caught in an infinite loop.
    """

    class Outer(AirtableModel):
        forward_ref: "Outer.Inner"

        class Inner(AirtableModel):
            pass

    # create an infinite loop
    Outer.Inner.Outer = Outer

    # This will cause RecursionError if we're not careful
    update_forward_refs(Outer)
