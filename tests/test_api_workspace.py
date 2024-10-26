import pytest

from pyairtable.api.base import Base
from pyairtable.api.workspace import Workspace


@pytest.fixture
def workspace_id():
    return "wspFakeWorkspaceId"


@pytest.fixture
def workspace(api, workspace_id):
    return Workspace(api, workspace_id)


@pytest.fixture
def mock_info(workspace, requests_mock, sample_json):
    return requests_mock.get(
        workspace.urls.meta, json=sample_json("WorkspaceCollaborators")
    )


def test_collaborators(workspace, mock_info):
    assert workspace.collaborators().id == "wspmhESAta6clCCwF"
    assert workspace.collaborators().name == "my first workspace"
    assert mock_info.call_count == 1


def test_name(workspace, mock_info):
    assert workspace.name == "my first workspace"
    assert mock_info.call_count == 1


def test_bases(workspace, mock_info):
    bases = workspace.bases()
    assert len(bases) == 2
    assert bases[0].id == "appLkNDICXNqxSDhG"
    assert bases[1].id == "appSW9R5uCNmRmfl6"
    assert mock_info.call_count == 1


def test_create_base(workspace, requests_mock, sample_json):
    url = workspace.api.urls.bases
    requests_mock.get(url, json=sample_json("Bases"))
    requests_mock.post(url, json={"id": "appLkNDICXNqxSDhG"})
    base = workspace.create_base("Base Name", [])
    assert isinstance(base, Base)
    assert base.id == "appLkNDICXNqxSDhG"


def test_delete(workspace, requests_mock):
    m = requests_mock.delete(
        workspace.urls.meta, json={"id": workspace.id, "deleted": True}
    )
    workspace.delete()
    assert m.call_count == 1


@pytest.mark.parametrize("workspace_param", ["workspace", "workspace_id"])
@pytest.mark.parametrize("base_param", ["base", "base_id"])
@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({}, {}),
        ({"index": 8}, {"targetIndex": 8}),
    ],
)
def test_move_base(
    workspace,
    workspace_id,
    workspace_param,
    base,
    base_id,
    base_param,
    kwargs,
    expected,
    requests_mock,
):
    m = requests_mock.post(workspace.urls.move_base)
    workspace.move_base(locals()[base_param], locals()[workspace_param], **kwargs)
    assert m.call_count == 1
    assert m.request_history[-1].json() == {
        "baseId": base_id,
        "targetWorkspaceId": workspace_id,
        **expected,
    }
