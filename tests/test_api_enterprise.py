from unittest.mock import Mock

import pytest

from pyairtable.api.enterprise import Enterprise
from pyairtable.models.schema import EnterpriseInfo, UserGroup, UserInfo


@pytest.fixture
def enterprise(api):
    return Enterprise(api, "entUBq2RGdihxl3vU")


@pytest.fixture
def enterprise_mocks(enterprise, requests_mock, sample_json):
    m = Mock()
    m.json_user = sample_json("UserInfo")
    m.json_users = {"users": [m.json_user]}
    m.json_group = sample_json("UserGroup")
    m.user_id = m.json_user["id"]
    m.group_id = m.json_group["id"]
    m.get_info = requests_mock.get(enterprise.url, json=sample_json("EnterpriseInfo"))
    m.get_users = requests_mock.get(f"{enterprise.url}/users", json=m.json_users)
    m.get_group = requests_mock.get(
        enterprise.api.build_url(f"meta/groups/{m.json_group['id']}"),
        json=m.json_group,
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
    assert enterprise_mocks.get_users.call_count == 1
    assert user.collaborations
    assert "appLkNDICXNqxSDhG" in user.collaborations.bases
    assert "pbdyGA3PsOziEHPDE" in user.collaborations.interfaces
    assert "wspmhESAta6clCCwF" in user.collaborations.workspaces


def test_user__no_collaboration(enterprise, enterprise_mocks):
    del enterprise_mocks.json_users["users"][0]["collaborations"]

    user = enterprise.user(enterprise_mocks.user_id, collaborations=False)
    assert isinstance(user, UserInfo)
    assert enterprise_mocks.get_users.call_count == 1
    assert not enterprise_mocks.get_users.last_request.qs.get("include")
    assert not user.collaborations  # test for Collaborations.__bool__
    assert not user.collaborations.bases
    assert not user.collaborations.interfaces
    assert not user.collaborations.workspaces


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


def test_group(enterprise, enterprise_mocks):
    grp = enterprise.group("ugp1mKGb3KXUyQfOZ")
    assert enterprise_mocks.get_group.call_count == 1
    assert isinstance(grp, UserGroup)
    assert grp.id == "ugp1mKGb3KXUyQfOZ"
    assert grp.name == "Group name"
    assert grp.members[0].email == "foo@bar.com"
    assert grp.collaborations
    assert "appLkNDICXNqxSDhG" in grp.collaborations.bases
    assert "pbdyGA3PsOziEHPDE" in grp.collaborations.interfaces
    assert "wspmhESAta6clCCwF" in grp.collaborations.workspaces


def test_group__no_collaboration(enterprise, enterprise_mocks):
    del enterprise_mocks.json_group["collaborations"]

    grp = enterprise.group(enterprise_mocks.group_id, collaborations=False)
    assert isinstance(grp, UserGroup)
    assert enterprise_mocks.get_group.call_count == 1
    assert not enterprise_mocks.get_group.last_request.qs.get("include")
    assert not grp.collaborations  # test for Collaborations.__bool__
    assert not grp.collaborations.bases
    assert not grp.collaborations.interfaces
    assert not grp.collaborations.workspaces
