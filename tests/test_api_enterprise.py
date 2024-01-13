import datetime
from unittest.mock import Mock, call, patch

import pytest

from pyairtable.api.enterprise import Enterprise
from pyairtable.models.schema import EnterpriseInfo, UserGroup, UserInfo
from pyairtable.testing import fake_id


@pytest.fixture
def enterprise(api):
    return Enterprise(api, "entUBq2RGdihxl3vU")


N_AUDIT_PAGES = 15
N_AUDIT_PAGE_SIZE = 10


@pytest.fixture(autouse=True)
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
    m.get_audit_log = requests_mock.get(
        enterprise.api.build_url(
            f"meta/enterpriseAccounts/{enterprise.id}/auditLogEvents"
        ),
        response_list=[
            {
                "json": {
                    "events": fake_audit_log_events(n),
                    "pagination": (
                        None if n == N_AUDIT_PAGES - 1 else {"previous": "dummy"}
                    ),
                }
            }
            for n in range(N_AUDIT_PAGES)
        ],
    )
    return m


def fake_audit_log_events(counter, page_size=N_AUDIT_PAGE_SIZE):
    return [
        {
            "id": str(counter * 1000 + n),
            "timestamp": datetime.datetime.now().isoformat(),
            "action": "viewBase",
            "actor": {"type": "anonymousUser"},
            "model_id": (base_id := fake_id("app")),
            "model_type": "base",
            "payload": {"name": "The Base Name"},
            "payloadVersion": "1.0",
            "context": {
                "baseId": base_id,
                "actionId": fake_id("act"),
                "enterpriseAccountId": fake_id("ent"),
                "workspaceId": fake_id("wsp"),
            },
            "origin": {"ipAddress": "8.8.8.8", "userAgent": "Internet Explorer"},
        }
        for n in range(page_size)
    ]


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
def test_users(enterprise, search_for):
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


@pytest.mark.parametrize(
    "fncall,expected_size",
    [
        (call(), N_AUDIT_PAGES * N_AUDIT_PAGE_SIZE),
        (call(page_limit=1), N_AUDIT_PAGE_SIZE),
    ],
)
def test_audit_log(enterprise, fncall, expected_size):
    events = [
        event
        for page in enterprise.audit_log(*fncall.args, **fncall.kwargs)
        for event in page.events
    ]
    assert len(events) == expected_size


def test_audit_log__no_loop(enterprise, requests_mock):
    """
    Test that an empty page of events does not cause an infinite loop.
    """
    requests_mock.get(
        enterprise.api.build_url(
            f"meta/enterpriseAccounts/{enterprise.id}/auditLogEvents"
        ),
        json={
            "events": [],
            "pagination": {"previous": "dummy"},
        },
    )
    events = [event for page in enterprise.audit_log() for event in page.events]
    assert len(events) == 0


@pytest.mark.parametrize(
    "fncall,sortorder,offset_field",
    [
        (call(), "descending", "previous"),
        (call(sort_asc=True), "ascending", "next"),
    ],
)
def test_audit_log__sortorder(
    api,
    enterprise,
    enterprise_mocks,
    fncall,
    sortorder,
    offset_field,
):
    with patch.object(api, "iterate_requests", wraps=api.iterate_requests) as m:
        list(enterprise.audit_log(*fncall.args, **fncall.kwargs))

    request = enterprise_mocks.get_audit_log.last_request
    assert request.qs["sortorder"] == [sortorder]
    assert m.mock_calls[-1].kwargs["offset_field"] == offset_field
