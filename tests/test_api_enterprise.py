from unittest.mock import Mock

import pytest

from pyairtable.api.enterprise import Enterprise
from pyairtable.models.schema import EnterpriseInfo, UserGroup, UserInfo


@pytest.fixture
def enterprise(api):
    return Enterprise(api, "entUBq2RGdihxl3vU")


@pytest.fixture
def enterprise_mocks(enterprise, requests_mock, sample_json):
    user_json = sample_json("UserInfo")
    group_json = sample_json("UserGroup")
    m = Mock()
    m.user_id = user_json["id"]
    m.get_info = requests_mock.get(
        enterprise.url,
        json=sample_json("EnterpriseInfo"),
    )
    m.get_user = requests_mock.get(
        f"{enterprise.url}/users/{m.user_id}",
        json=user_json,
    )
    m.get_users = requests_mock.get(
        f"{enterprise.url}/users",
        json={"users": [user_json]},
    )
    m.get_group = requests_mock.get(
        enterprise.api.build_url(f"meta/groups/{group_json['id']}"),
        json=group_json,
    )
    return m


def test_info(enterprise, enterprise_mocks):
    assert isinstance(info := enterprise.info(), EnterpriseInfo)
    assert info.id == "entUBq2RGdihxl3vU"
    assert info.workspace_ids == ["wspmhESAta6clCCwF", "wspHvvm4dAktsStZH"]
    assert info.email_domains[0].is_sso_required is True
    assert enterprise_mocks.get_info.call_count == 1

    assert enterprise.info(force=True).id == "entUBq2RGdihxl3vU"
    assert enterprise_mocks.get_info.call_count == 2


def test_user(enterprise, enterprise_mocks):
    user = enterprise.user(enterprise_mocks.user_id)
    assert isinstance(user, UserInfo)
    assert enterprise_mocks.get_user.call_count == 1


@pytest.mark.parametrize(
    "search_for",
    (
        ["usrL2PNC5o3H4lBEi"],
        ["foo@bar.com"],
        ["usrL2PNC5o3H4lBEi", "foo@bar.com"],  # should not return duplicates
    ),
)
def test_users(enterprise, enterprise_mocks, search_for):
    results = enterprise.users(search_for)
    assert len(results) == 1
    assert isinstance(user := results[0], UserInfo)
    assert user.id == "usrL2PNC5o3H4lBEi"
    assert user.state == "provisioned"


def test_users__invalid_value(enterprise, enterprise_mocks):
    with pytest.raises(ValueError):
        enterprise.users(["not an ID or email"])


def test_group(enterprise, enterprise_mocks):
    info = enterprise.group("ugp1mKGb3KXUyQfOZ")
    assert enterprise_mocks.get_group.call_count == 1
    assert isinstance(info, UserGroup)
    assert info.id == "ugp1mKGb3KXUyQfOZ"
    assert info.name == "Group name"
    assert info.members[0].email == "foo@bar.com"
