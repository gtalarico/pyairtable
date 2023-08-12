from typing import Any, Dict, List, Optional, Sequence

from pyairtable.models.schema import WorkspaceInfo
from pyairtable.utils import enterprise_only


class Workspace:
    """
    Represents an Airtable workspace, which contains a number of bases
    and its own set of collaborators.

    >>> ws = api.workspace("wspmhESAta6clCCwF")
    >>> ws.info().name
    'my first workspace'
    >>> ws.create_base("Base Name", tables=[...])
    <pyairtable.Base base_id="appMhESAta6clCCwF">

    Most workspace functionality is limited to users on Enterprise billing plans.
    """

    def __init__(self, api: "pyairtable.api.api.Api", workspace_id: str):
        self.api = api
        self.id = workspace_id
        self._info: Optional[WorkspaceInfo] = None

    @property
    def url(self) -> str:
        return self.api.build_url("meta/workspaces", self.id)

    def create_base(
        self,
        name: str,
        tables: Sequence[Dict[str, Any]],
    ) -> "pyairtable.api.base.Base":
        """
        Creates a base in the given workspace.

        Args:
            name: The name to give to the new base. Does not need to be unique.
            tables: A list of ``dict`` objects that conform to Airtable's
                `Table model <https://airtable.com/developers/web/api/model/table-model>`__.
        """
        url = self.api.build_url("meta/bases")
        payload = {"name": name, "workspaceId": self.id, "tables": list(tables)}
        response = self.api.request("POST", url, json=payload)
        return self.api.base(response["id"], validate=True)

    # Everything below here requires .info() and is therefore Enterprise-only

    @enterprise_only
    def info(self, *, force: bool = False) -> WorkspaceInfo:
        """
        Retrieves basic information, collaborators, and invites
        for the given workspace, caching the result.

        Args:
            force: |kwarg_force_metadata|
        """
        if force or not self._info:
            params = {"include": ["collaborators", "inviteLinks"]}
            payload = self.api.request("GET", self.url, params=params)
            self._info = WorkspaceInfo.parse_obj(payload)
        return self._info

    @enterprise_only
    def bases(self) -> List["pyairtable.api.base.Base"]:
        """
        Retrieves all bases within the workspace.
        """
        return [self.api.base(base_id) for base_id in self.info().base_ids]

    @property
    @enterprise_only
    def name(self) -> str:
        """
        The name of the workspace.
        """
        return self.info().name


# These are at the bottom of the module to avoid circular imports
import pyairtable.api.api  # noqa
import pyairtable.api.base  # noqa
