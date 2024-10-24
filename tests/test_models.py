from datetime import datetime, timezone
from typing import List

import pytest

from pyairtable.models._base import (
    AirtableModel,
    CanDeleteModel,
    CanUpdateModel,
    RestfulModel,
    rebuild_models,
)


@pytest.fixture
def raw_data():
    return {"foo": 1, "bar": 2, "baz": 3}


@pytest.fixture
def create_instance(api, raw_data):
    def _creates_instance(**kwargs):
        # These kwargs used to be interpreted by __init_subclass__ but now that behavior
        # is controlled by mixins. This weirdness is just to avoid redoing our tests.
        base_classes = []
        if kwargs.pop("allow_update", True):
            base_classes.append(CanUpdateModel)
        if kwargs.pop("allow_delete", True):
            base_classes.append(CanDeleteModel)

        kwargs.setdefault("url", "https://example.com/{self.foo}/{self.bar}/{self.baz}")

        class Subclass(*base_classes, **kwargs):
            foo: int
            bar: int
            baz: int

        return Subclass.from_api(raw_data, api)

    return _creates_instance


def test_raw(api):
    """
    Test that AirtableModel.from_api saves the raw value, so that developers
    can access the exact payload we received from the API. This is mostly
    in case Airtable adds new things to webhooks or schemas in the future.
    """

    class Grandchild(AirtableModel):
        value: int

    class Child(AirtableModel):
        grandchild: Grandchild

    class Parent(AirtableModel):
        child: Child

    raw = {"child": {"grandchild": {"value": 1}}, "foo": "FOO", "bar": "BAR"}
    obj = Parent.from_api(raw, api)
    assert not hasattr(obj, "foo")
    assert not hasattr(obj, "bar")
    assert obj._raw == raw
    assert obj.child._raw == raw["child"]
    assert obj.child.grandchild._raw == raw["child"]["grandchild"]


@pytest.mark.parametrize("prefix", ["https://api.airtable.com/v0/prefix", "prefix"])
def test_from_api(raw_data, prefix, api):
    """
    Test that CanUpdate.from_api persists its parameters correctly,
    and that if `url=` is passed to the subclass, we'll always get a valid URL.
    """

    class Dummy(CanUpdateModel, url="{prefix}/foo={self.foo}/bar={self.bar}"):
        foo: int
        bar: int

    obj = Dummy.from_api(raw_data, api, context={"prefix": prefix})
    assert obj._api == api
    assert obj._raw == raw_data
    assert obj._url == "https://api.airtable.com/v0/prefix/foo=1/bar=2"
    assert obj.foo == 1
    assert obj.bar == 2
    assert not hasattr(obj, "baz")
    assert obj._raw["baz"] == 3


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
    with pytest.raises(AttributeError):
        obj.save()


def test_save_without_url(create_instance):
    """
    Test that if we do not provide context for computing a URL when an instance
    is created, we won't be able to save it later.
    """
    obj = create_instance(url="")
    with pytest.raises(RuntimeError):
        obj.save()


def test_save__nested_reload(requests_mock, api):
    """
    Test that reloading an object with nested models correctly reloads all of them,
    while preserving those nested models' access to the API.
    """

    class Parent(CanUpdateModel, url="foo/{self.id}"):
        id: int
        name: str
        children: List["Parent.Child"]  # noqa

        class Child(CanUpdateModel, url="foo/{parent.id}/child/{child.id}"):
            id: int
            name: str

    rebuild_models(Parent)

    parent_data = {
        "id": 1,
        "name": "One",
        "children": [
            (child2_data := {"id": 2, "name": "Two"}),
            (child3_data := {"id": 3, "name": "Three"}),
        ],
    }
    requests_mock.get(parent_url := api.build_url("foo/1"), json=parent_data)
    requests_mock.get(child2_url := api.build_url("foo/1/child/2"), json=child2_data)
    requests_mock.get(child3_url := api.build_url("foo/1/child/3"), json=child3_data)

    parent = Parent.from_api(parent_data, api)
    assert parent.name == "One"
    assert parent.children[0].name == "Two"

    # Test that we can still reload the parent object
    m_parent_patch = requests_mock.patch(
        parent_url,
        json={
            **parent_data,
            "name": (parent_update := "One Updated"),
        },
    )
    parent.name = parent_update
    parent.save()
    assert m_parent_patch.call_count == 1
    assert m_parent_patch.last_request.json()["name"] == parent_update

    # Test that we can still patch a nested object after its parent was reloaded,
    # because we saved the URL context from `from_api()` and reused it on `_reload()`.
    m_child2_patch = requests_mock.patch(child2_url, json=child2_data)
    m_child3_patch = requests_mock.patch(
        child3_url,
        json={
            **child3_data,
            "name": (child3_update := "Three Updated"),
        },
    )
    parent.children[1].name = child3_update
    parent.children[1].save()
    assert m_child3_patch.call_count == 1
    assert m_child3_patch.last_request.json()["name"] == child3_update
    assert parent.children[1].name == child3_update
    assert m_child2_patch.call_count == 0  # just to be sure


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
    with pytest.raises(AttributeError):
        obj.delete()


def test_delete_without_url(create_instance):
    """
    Test that if we do not provide context for computing a URL when an instance
    is created, we won't be able to delete it later.
    """
    obj = create_instance(url="")
    with pytest.raises(RuntimeError):
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
    rebuild_models(Outer)


def test_restfulmodel__set_url(api, base):
    """
    Test that the RestfulModel class generates a URL based on API context.
    Also test that RestfulModel puts the full URL context into certain types
    of exceptions that occur during URL formatting.
    """

    class Dummy(RestfulModel, url="{base.id}/{dummy.one}/{dummy.two}"):
        one: int
        two: str

    data = {"one": 1, "two": "2"}

    d = Dummy.from_api(data, api, context={"base": base})
    assert d._url == api.build_url(f"{base.id}/1/2")

    with pytest.raises(KeyError) as exc_info:
        Dummy.from_api(data, api)

    assert exc_info.match(r"\('base', \{'dummy': .*\}\)")

    with pytest.raises(AttributeError) as exc_info:
        Dummy.from_api(data, api, context={"base": None})

    assert exc_info.match(
        r'"\'NoneType\' object has no attribute \'id\'"'
        r", \{'base': None, 'dummy': Dummy\(.*\)\}"
    )


def test_datetime_conversion(api, requests_mock):
    """
    Test that if an AirtableModel field is specified as a datetime,
    and the input data is provided as a str, we'll convert to a datetime
    and back to a str when saving.
    """

    class Dummy(CanUpdateModel, url="{self.id}", writable=["timestamp"]):
        id: str
        timestamp: datetime

    data = {"id": "rec000", "timestamp": "2024-01-08T12:34:56Z"}
    obj = Dummy.from_api(data, api)
    assert obj.timestamp == datetime(2024, 1, 8, 12, 34, 56, tzinfo=timezone.utc)
    m = requests_mock.patch(obj._url, json=data)
    obj.save()
    assert m.call_count == 1
    assert m.request_history[0].json() == {"timestamp": "2024-01-08T12:34:56.000Z"}


@pytest.mark.parametrize(
    "attrpath",
    [
        "pyairtable.models.webhook.Webhook.last_successful_notification_time",
        "pyairtable.models.webhook.Webhook.expiration_time",
        "pyairtable.models.comment.Comment.created_time",
        "pyairtable.models.comment.Comment.last_updated_time",
        "pyairtable.models.webhook.WebhookNotification.timestamp",
        "pyairtable.models.webhook.WebhookPayload.timestamp",
        "pyairtable.models.audit.AuditLogResponse.events[0].timestamp",
        "pyairtable.models.schema.BaseCollaborators.group_collaborators.via_base[0].created_time",
        "pyairtable.models.schema.BaseCollaborators.individual_collaborators.via_base[0].created_time",
        "pyairtable.models.schema.BaseCollaborators.interfaces['pbdLkNDICXNqxSDhG'].created_time",
        "pyairtable.models.schema.BaseCollaborators.interfaces['pbdLkNDICXNqxSDhG'].first_publish_time",
        "pyairtable.models.schema.BaseShares.shares[0].created_time",
        "pyairtable.models.schema.WorkspaceCollaborators.invite_links.via_base[0].created_time",
        "pyairtable.models.schema.EnterpriseInfo.created_time",
        "pyairtable.models.schema.WorkspaceCollaborators.created_time",
        "pyairtable.models.schema.WorkspaceCollaborators.invite_links.via_base[0].created_time",
        "pyairtable.models.schema.UserGroup.created_time",
        "pyairtable.models.schema.UserGroup.updated_time",
        "pyairtable.models.schema.UserGroup.members[1].created_time",
        "pyairtable.models.schema.UserInfo.created_time",
        "pyairtable.models.schema.UserInfo.last_activity_time",
    ],
)
def test_datetime_models(attrpath, schema_obj):
    """
    Test that specific models' fields are correctly converted to datetimes.
    """
    assert isinstance(schema_obj(attrpath), datetime)
