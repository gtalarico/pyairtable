from datetime import datetime, timezone
from unittest.mock import Mock, call, patch

import pytest

from pyairtable.api.enterprise import DeleteUsersResponse, ManageUsersResponse
from pyairtable.models.schema import EnterpriseInfo, UserGroup, UserInfo
from pyairtable.testing import fake_id

N_AUDIT_PAGES = 15
N_AUDIT_PAGE_SIZE = 10


@pytest.fixture(autouse=True)
def enterprise_mocks(enterprise, requests_mock, sample_json):
    m = Mock()
    m.json_user = sample_json("UserInfo")
    m.json_users = {"users": [m.json_user]}
    m.json_group = sample_json("UserGroup")
    m.json_enterprise = sample_json("EnterpriseInfo")
    m.user_id = m.json_user["id"]
    m.group_id = m.json_group["id"]
    m.get_info = requests_mock.get(
        enterprise_url := "https://api.airtable.com/v0/meta/enterpriseAccounts/entUBq2RGdihxl3vU",
        json=m.json_enterprise,
    )
    m.get_user = requests_mock.get(
        f"{enterprise_url}/users/usrL2PNC5o3H4lBEi",
        json=m.json_user,
    )
    m.get_users = requests_mock.get(
        f"{enterprise_url}/users",
        json=m.json_users,
    )
    m.get_group = requests_mock.get(
        "https://api.airtable.com/v0/meta/groups/ugp1mKGb3KXUyQfOZ",
        json=m.json_group,
    )
    m.get_audit_log = requests_mock.get(
        f"{enterprise_url}/auditLogEvents",
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
    m.remove_user = requests_mock.post(
        f"{enterprise_url}/users/{m.user_id}/remove",
        json=sample_json("UserRemoved"),
    )
    m.claim_users = requests_mock.post(
        f"{enterprise_url}/claim/users",
        json={"errors": []},
    )
    return m


def fake_audit_log_events(counter, page_size=N_AUDIT_PAGE_SIZE):
    return [
        {
            "id": str(counter * 1000 + n),
            "timestamp": datetime.now().isoformat(),
            "action": "viewBase",
            "actor": {"type": "anonymousUser"},
            "modelId": (base_id := fake_id("app")),
            "modelType": "base",
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
    assert "aggregated" not in enterprise_mocks.get_info.last_request.qs
    assert "descendants" not in enterprise_mocks.get_info.last_request.qs


def test_info__aggregated_descendants(enterprise, enterprise_mocks):
    enterprise_mocks.json_enterprise["aggregated"] = {
        "groupIds": ["ugp1mKGb3KXUyQfOZ"],
        "userIds": ["usrL2PNC5o3H4lBEi"],
        "workspaceIds": ["wspmhESAta6clCCwF"],
    }
    enterprise_mocks.json_enterprise["descendants"] = {
        (sub_ent_id := fake_id("ent")): {
            "groupIds": ["ugp1mKGb3KXUyDESC"],
            "userIds": ["usrL2PNC5o3H4DESC"],
            "workspaceIds": ["wspmhESAta6clDESC"],
        }
    }
    info = enterprise.info(aggregated=True, descendants=True)
    assert enterprise_mocks.get_info.call_count == 1
    assert enterprise_mocks.get_info.last_request.qs["include"] == [
        "aggregated",
        "descendants",
    ]
    assert info.aggregated.group_ids == ["ugp1mKGb3KXUyQfOZ"]
    assert info.aggregated.user_ids == ["usrL2PNC5o3H4lBEi"]
    assert info.aggregated.workspace_ids == ["wspmhESAta6clCCwF"]
    assert info.descendants[sub_ent_id].group_ids == ["ugp1mKGb3KXUyDESC"]
    assert info.descendants[sub_ent_id].user_ids == ["usrL2PNC5o3H4DESC"]
    assert info.descendants[sub_ent_id].workspace_ids == ["wspmhESAta6clDESC"]


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


def test_user__descendants(enterprise, enterprise_mocks):
    enterprise_mocks.json_users["users"][0]["descendants"] = {
        (other_ent_id := fake_id("ent")): {
            "lastActivityTime": "2021-01-01T12:34:56Z",
            "isAdmin": True,
            "groups": [{"id": (fake_group_id := fake_id("ugp"))}],
        }
    }
    user = enterprise.user(enterprise_mocks.user_id, descendants=True)
    d = user.descendants[other_ent_id]
    assert d.last_activity_time == datetime(2021, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
    assert d.is_admin is True
    assert d.groups[0].id == fake_group_id


def test_user__aggregates(enterprise, enterprise_mocks):
    enterprise_mocks.json_users["users"][0]["aggregated"] = {
        "lastActivityTime": "2021-01-01T12:34:56Z",
        "isAdmin": True,
        "groups": [{"id": (fake_group_id := fake_id("ugp"))}],
    }
    user = enterprise.user(enterprise_mocks.user_id, aggregated=True)
    a = user.aggregated
    assert a.last_activity_time == datetime(2021, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
    assert a.is_admin is True
    assert a.groups[0].id == fake_group_id


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


def test_users__descendants(enterprise, enterprise_mocks):
    enterprise_mocks.json_users["users"][0]["descendants"] = {
        (other_ent_id := fake_id("ent")): {
            "lastActivityTime": "2021-01-01T12:34:56Z",
            "isAdmin": True,
            "groups": [{"id": (fake_group_id := fake_id("ugp"))}],
        }
    }
    users = enterprise.users([enterprise_mocks.user_id], descendants=True)
    assert len(users) == 1
    d = users[0].descendants[other_ent_id]
    assert d.last_activity_time == datetime(2021, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
    assert d.is_admin is True
    assert d.groups[0].id == fake_group_id


def test_users__aggregates(enterprise, enterprise_mocks):
    enterprise_mocks.json_users["users"][0]["aggregated"] = {
        "lastActivityTime": "2021-01-01T12:34:56Z",
        "isAdmin": True,
        "groups": [{"id": (fake_group_id := fake_id("ugp"))}],
    }
    users = enterprise.users([enterprise_mocks.user_id], aggregated=True)
    assert len(users) == 1
    a = users[0].aggregated
    assert a.last_activity_time == datetime(2021, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
    assert a.is_admin is True
    assert a.groups[0].id == fake_group_id


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
    """
    Test that we iterate through multiple pages of the audit log. correctly
    """
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
    """
    Test that we calculate sortorder and offset_field correctly
    dpeending on whether we're ascending or descending.
    """
    with patch.object(api, "iterate_requests", wraps=api.iterate_requests) as m:
        list(enterprise.audit_log(*fncall.args, **fncall.kwargs))

    request = enterprise_mocks.get_audit_log.last_request
    assert request.qs["sortOrder"] == [sortorder]
    assert m.mock_calls[-1].kwargs["offset_field"] == offset_field


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        (
            {},
            {"isDryRun": False},
        ),
        (
            {"replacement": "otherUser"},
            {"isDryRun": False, "replacementOwnerId": "otherUser"},
        ),
    ],
)
def test_remove_user(enterprise, enterprise_mocks, kwargs, expected):
    removed = enterprise.remove_user(enterprise_mocks.user_id, **kwargs)
    assert enterprise_mocks.remove_user.call_count == 1
    assert enterprise_mocks.remove_user.last_request.json() == expected
    assert removed.shared.workspaces[0].user_id == "usrL2PNC5o3H4lBEi"


@pytest.fixture
def user_info(enterprise, enterprise_mocks):
    user_info = enterprise.user(enterprise_mocks.user_id)
    assert user_info._url == f"{enterprise.urls.users}/{user_info.id}"
    return user_info


def test_delete_user(user_info, requests_mock):
    m = requests_mock.delete(user_info._url)
    user_info.delete()
    assert m.call_count == 1


def test_manage_user(user_info, requests_mock):
    m = requests_mock.patch(user_info._url)
    user_info.save()
    assert m.call_count == 1
    assert m.last_request.json() == {"email": "foo@bar.com", "state": "provisioned"}


def test_logout_user(user_info, requests_mock):
    m = requests_mock.post(user_info._url + "/logout")
    user_info.logout()
    assert m.call_count == 1
    assert m.last_request.body is None


def test_claim_users(enterprise, enterprise_mocks):
    result = enterprise.claim_users(
        {
            "usrFakeUserId": "managed",
            "someone@example.com": "unmanaged",
        }
    )
    assert isinstance(result, ManageUsersResponse)
    assert enterprise_mocks.claim_users.call_count == 1
    assert enterprise_mocks.claim_users.last_request.json() == {
        "users": [
            {"id": "usrFakeUserId", "state": "managed"},
            {"email": "someone@example.com", "state": "unmanaged"},
        ]
    }


def test_delete_users(enterprise, requests_mock):
    response = {
        "deletedUsers": [{"email": "foo@bar.com", "id": "usrL2PNC5o3H4lBEi"}],
        "errors": [
            {
                "email": "bar@bam.com",
                "message": "Invalid permissions",
                "type": "INVALID_PERMISSIONS",
            }
        ],
    }
    emails = [f"foo{n}@bar.com" for n in range(5)]
    m = requests_mock.delete(enterprise.urls.users, json=response)
    parsed = enterprise.delete_users(emails)
    assert m.call_count == 1
    assert m.last_request.qs == {"email": emails}
    assert isinstance(parsed, DeleteUsersResponse)
    assert parsed.deleted_users[0].email == "foo@bar.com"
    assert parsed.errors[0].type == "INVALID_PERMISSIONS"


@pytest.mark.parametrize("action", ["grant", "revoke"])
def test_manage_admin_access(enterprise, enterprise_mocks, requests_mock, action):
    user = enterprise.user(enterprise_mocks.user_id)
    m = requests_mock.post(enterprise.urls.admin_access(action), json={})
    method = getattr(enterprise, f"{action}_admin")
    result = method(
        fake_user_id := fake_id("usr"),
        fake_email := "fake@example.com",
        user,
    )
    assert isinstance(result, ManageUsersResponse)
    assert m.call_count == 1
    assert m.last_request.json() == {
        "users": [
            {"id": fake_user_id},
            {"email": fake_email},
            {"id": user.id},
        ]
    }
