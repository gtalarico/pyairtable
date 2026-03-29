from functools import cached_property
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Union

from pyairtable.models.schema import WorkspaceCollaborators
from pyairtable.utils import Url, UrlBuilder, cache_unless_forced, enterprise_only

if TYPE_CHECKING:
    from pyairtable.api.api import Api
    from pyairtable.api.base import Base


class Workspace:
    """
    Represents an Airtable workspace, which contains a number of bases
    and its own set of collaborators.

    >>> ws = api.workspace("wspmhESAta6clCCwF")
    >>> ws.collaborators().name
    'my first workspace'
    >>> ws.create_base("Base Name", tables=[...])
    <pyairtable.Base base_id="appMhESAta6clCCwF">

    Most workspace functionality is limited to users on Enterprise billing plans.
    """

    _collaborators: Optional[WorkspaceCollaborators] = None

    class _urls(UrlBuilder):
        #: URL for retrieving the workspace's metadata and collaborators.
        meta = Url("meta/workspaces/{id}")

        #: URL for moving a base to a new workspace.
        move_base = meta / "moveBase"

        #: URL for POST requests that modify collaborations on the workspace.
        collaborators = meta / "collaborators"

    urls = cached_property(_urls)

    def __init__(self, api: "Api", workspace_id: str):
        self.api = api
        self.id = workspace_id

    def create_base(
        self,
        name: str,
        tables: Sequence[Dict[str, Any]],
    ) -> "Base":
        """
        Create a base in the given workspace.

        See https://airtable.com/developers/web/api/create-base

        Args:
            name: The name to give to the new base. Does not need to be unique.
            tables: A list of ``dict`` objects that conform to Airtable's
                `Table model <https://airtable.com/developers/web/api/model/table-model>`__.
        """
        url = self.api.urls.bases
        payload = {"name": name, "workspaceId": self.id, "tables": list(tables)}
        response = self.api.post(url, json=payload)
        return self.api.base(response["id"], validate=True, force=True)

    # Everything below here requires .info() and is therefore Enterprise-only

    @enterprise_only
    @cache_unless_forced
    def collaborators(self) -> WorkspaceCollaborators:
        """
        Retrieve basic information, collaborators, and invite links
        for the given workspace, caching the result.

        See https://airtable.com/developers/web/api/get-workspace-collaborators
        """
        params = {"include": ["collaborators", "inviteLinks"]}
        payload = self.api.get(self.urls.meta, params=params)
        return WorkspaceCollaborators.from_api(payload, self.api, context=self)

    @enterprise_only
    def bases(self) -> List["Base"]:
        """
        Retrieve all bases within the workspace.
        """
        return [self.api.base(base_id) for base_id in self.collaborators().base_ids]

    @property
    @enterprise_only
    def name(self) -> str:
        """
        The name of the workspace.
        """
        return self.collaborators().name

    @enterprise_only
    def delete(self) -> None:
        """
        Delete the workspace.

        See https://airtable.com/developers/web/api/delete-workspace

        Usage:
            >>> ws = api.workspace("wspmhESAta6clCCwF")
            >>> ws.delete()
        """
        self.api.delete(self.urls.meta)

    @enterprise_only
    def move_base(
        self,
        base: Union[str, "Base"],
        target: Union[str, "Workspace"],
        index: Optional[int] = None,
    ) -> None:
        """
        Move the given base to a new workspace.

        See https://airtable.com/developers/web/api/move-base

        Usage:
            >>> base = api.base("appCwFmhESAta6clC")
            >>> ws = api.workspace("wspmhESAta6clCCwF")
            >>> ws.move_base(base, "wspSomeOtherPlace", index=0)
        """
        base_id = base if isinstance(base, str) else base.id
        target_id = target if isinstance(target, str) else target.id
        payload: Dict[str, Any] = {"baseId": base_id, "targetWorkspaceId": target_id}
        if index is not None:
            payload["targetIndex"] = index
        self.api.post(self.urls.move_base, json=payload)
