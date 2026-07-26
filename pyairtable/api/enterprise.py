from collections.abc import Iterable, Iterator, Sequence
from datetime import date, datetime
from functools import cached_property, partialmethod
from typing import TYPE_CHECKING, Any, Literal

import pydantic
from typing_extensions import Self

from pyairtable.exceptions import InvalidParameterError, MissingRecordError
from pyairtable.models._base import AirtableModel, rebuild_models
from pyairtable.models.audit import AuditLogResponse
from pyairtable.models.schema import (
    EnterpriseInfo,
    NestedId,
    Package,
    UserGroup,
    UserInfo,
)
from pyairtable.utils import (
    Url,
    UrlBuilder,
    cache_unless_forced,
    coerce_iso_str,
    coerce_list_str,
    enterprise_only,
)

if TYPE_CHECKING:
    from pyairtable.api.api import Api
    from pyairtable.api.base import Base
    from pyairtable.api.workspace import Workspace


@enterprise_only
class Enterprise:
    """
    Represents an Airtable enterprise account.

    >>> enterprise = api.enterprise("entUBq2RGdihxl3vU")
    >>> enterprise.info().workspace_ids
    ['wspmhESAta6clCCwF', ...]
    """

    class _urls(UrlBuilder):
        #: URL for retrieving basic information about the enterprise.
        meta = Url("meta/enterpriseAccounts/{id}")

        #: URL for retrieving information about all users.
        users = meta / "users"

        #: URL for retrieving information about all user groups.
        groups = Url("meta/groups")

        #: URL for claiming a user into an enterprise.
        claim_users = meta / "claim/users"

        #: URL for retrieving audit log events.
        audit_log = meta / "auditLogEvents"

        #: URL for managing descendant enterprise accounts.
        descendants = meta / "descendants"

        #: URL for moving user groups between enterprise accounts.
        move_groups = meta / "moveGroups"

        #: URL for moving workspaces between enterprise accounts.
        move_workspaces = meta / "moveWorkspaces"

        #: URL for creating a new workspace.
        create_workspace = Url("meta/workspaces")

        #: URL for listing enterprise packages.
        packages = meta / "packages"

        #: URL for listing personal access tokens.
        access_tokens = meta / "personalAccessTokens"

        #: URL for revoking personal access tokens.
        revoke_access_tokens = access_tokens / "revoke"

        #: URL for updating the workspace AI allowlist.
        workspace_ai_allowlist = meta / "workspaceAiAllowlist"

        def package_install(self, package_id: str) -> Url:
            """
            URL for installing a package (creating a base from a package).
            """
            return self.meta / "packages" / package_id / "install"

        def user(self, user_id: str) -> Url:
            """
            URL for retrieving information about a single user.
            """
            return self.users / user_id

        def group(self, group_id: str) -> Url:
            """
            URL for retrieving information about a single user group.
            """
            return self.groups / group_id

        def admin_access(self, action: Literal["grant", "revoke"]) -> Url:
            """
            URL for granting or revoking admin access to one or more users.
            """
            return self.meta / f"users/{action}AdminAccess"

        def remove_user(self, user_id: str) -> Url:
            """
            URL for removing a user from the enterprise.
            """
            return self.user(user_id) / "remove"

        #: URL for granting admin access to one or more users.
        grant_admin = partialmethod(admin_access, "grant")

        #: URL for revoking admin access from one or more users.
        revoke_admin = partialmethod(admin_access, "revoke")

    urls = cached_property(_urls)

    def __init__(self, api: "Api", enterprise_id: str):
        self.api = api
        self.id = enterprise_id
        self._info: EnterpriseInfo | None = None

    @cache_unless_forced
    def info(
        self,
        *,
        aggregated: bool = False,
        descendants: bool = False,
    ) -> EnterpriseInfo:
        """
        Retrieve basic information about the enterprise, caching the result.
        Calls `Get enterprise <https://airtable.com/developers/web/api/get-enterprise>`__.

        Args:
            aggregated: if ``True``, include aggregated values across the enterprise.
            descendants: if ``True``, include information about the enterprise's descendant orgs.
        """
        include = []
        if aggregated:
            include.append("aggregated")
        if descendants:
            include.append("descendants")
        params = {"include": include}
        response = self.api.get(self.urls.meta, params=params)
        return EnterpriseInfo.from_api(response, self.api)

    def group(self, group_id: str, collaborations: bool = True) -> UserGroup:
        """
        Retrieve information on a single user group with the given ID.

        Args:
            group_id: A user group ID (``grpQBq2RGdihxl3vU``).
            collaborations: If ``False``, no collaboration data will be requested
                from Airtable. This may result in faster responses.
        """
        params = {"include": ["collaborations"] if collaborations else []}
        payload = self.api.get(self.urls.group(group_id), params=params)
        return UserGroup.model_validate(payload)

    def user(
        self,
        id_or_email: str,
        *,
        collaborations: bool = True,
        aggregated: bool = False,
        descendants: bool = False,
    ) -> UserInfo:
        """
        Retrieve information on a single user with the given ID or email.

        Args:
            id_or_email: A user ID (``usrQBq2RGdihxl3vU``) or email address.
            collaborations: If ``False``, no collaboration data will be requested
                from Airtable. This may result in faster responses.
            aggregated: If ``True``, includes the user's aggregated values
                across this enterprise account and its descendants.
            descendants: If ``True``, includes information about the user
                in a ``dict`` keyed per descendant enterprise account.
        """
        users = self.users(
            [id_or_email],
            collaborations=collaborations,
            aggregated=aggregated,
            descendants=descendants,
        )
        return users[0]

    def users(
        self,
        ids_or_emails: Iterable[str],
        *,
        collaborations: bool = True,
        aggregated: bool = False,
        descendants: bool = False,
    ) -> list[UserInfo]:
        """
        Retrieve information on the users with the given IDs or emails.

        Read more at `Get users by ID or email <https://airtable.com/developers/web/api/get-users-by-id-or-email>`__.

        Args:
            ids_or_emails: A sequence of user IDs (``usrQBq2RGdihxl3vU``)
                or email addresses (or both).
            collaborations: If ``False``, no collaboration data will be requested
                from Airtable. This may result in faster responses.
            aggregated: If ``True``, includes the user's aggregated values
                across this enterprise account and its descendants.
            descendants: If ``True``, includes information about the user
                in a ``dict`` keyed per descendant enterprise account.
        """
        user_ids: list[str] = []
        emails: list[str] = []
        for value in ids_or_emails:
            (emails if "@" in value else user_ids).append(value)

        include = []
        if collaborations:
            include.append("collaborations")
        if aggregated:
            include.append("aggregated")
        if descendants:
            include.append("descendants")

        response = self.api.get(
            url=self.urls.users,
            params={
                "id": user_ids,
                "email": emails,
                "include": include,
            },
        )
        # key by user ID to avoid returning duplicates
        users = {
            info.id: info
            for user_obj in response["users"]
            if (info := UserInfo.from_api(user_obj, self.api, context=self))
        }
        return list(users.values())

    def audit_log(
        self,
        *,
        page_size: int | None = None,
        page_limit: int | None = None,
        sort_asc: bool | None = False,
        previous: str | None = None,
        next: str | None = None,
        start_time: str | date | datetime | None = None,
        end_time: str | date | datetime | None = None,
        user_id: str | Iterable[str] | None = None,
        event_type: str | Iterable[str] | None = None,
        model_id: str | Iterable[str] | None = None,
        category: str | Iterable[str] | None = None,
    ) -> Iterator[AuditLogResponse]:
        """
        Retrieve and yield results from the `Audit Log <https://airtable.com/developers/web/api/audit-logs-integration-guide>`__,
        one page of results at a time. Each result is an instance of :class:`~pyairtable.models.audit.AuditLogResponse`
        and contains the pagination IDs returned from the API, as described in the linked documentation.

        By default, the Airtable API will return up to 180 days of audit log events, going backwards from most recent.
        Retrieving all records may take some time, but is as straightforward as:

            >>> enterprise = Enterprise("entYourEnterpriseId")
            >>> events = [
            ...     event
            ...     for page in enterprise.audit_log()
            ...     for event in page.events
            ... ]

        If you are creating a record of all audit log events, you probably want to start with the earliest
        events in the retention window and iterate chronologically. You'll likely have a job running
        periodically in the background, so you'll need some way to persist the pagination IDs retrieved
        from the API in case that job is interrupted and needs to be restarted.

        The sample code below will use a local file to remember the next page's ID, so that if the job is
        interrupted, it will resume where it left off (potentially processing some entries twice).

        .. code-block:: python

            import os
            import shelve
            import pyairtable

            def handle_event(event):
                print(event)

            api = pyairtable.Api(os.environ["AIRTABLE_API_KEY"])
            enterprise = api.enterprise(os.environ["AIRTABLE_ENTERPRISE_ID"])
            persistence = shelve.open("audit_log.db")
            first_page = persistence.get("next", None)

            for page in enterprise.audit_log(sort_asc=True, next=first_page):
                for event in page.events:
                    handle_event(event)
                persistence["next"] = page.pagination.next

        For more information on any of the keyword parameters below, refer to the
        `audit log events <https://airtable.com/developers/web/api/audit-log-events>`__
        API documentation.

        Args:
            page_size: How many events per page to return (maximum 100).
            page_limit: How many pages to return before stopping.
            sort_asc: Whether to sort in ascending order (earliest to latest)
                rather than descending order (latest to earliest).
            previous: Requests the previous page of results from the given ID.
                See the `audit log integration guide <https://airtable.com/developers/web/api/audit-logs-integration-guide>`__
                for more information on pagination parameters.
            next: Requests the next page of results according to the given ID.
                See the `audit log integration guide <https://airtable.com/developers/web/api/audit-logs-integration-guide>`__
                for more information on pagination parameters.
            start_time: Earliest timestamp to retrieve (inclusive).
            end_time: Latest timestamp to retrieve (inclusive).
            user_id: Retrieve audit log events originating
                from the provided user ID or IDs (maximum 100).
            event_type: Retrieve audit log events falling under the provided
                `audit log event type <https://airtable.com/developers/web/api/audit-log-event-types>`__
                or types (maximum 100).
            model_id: Retrieve audit log events taking action on, or involving,
                the provided model ID or IDs (maximum 100).
            category: Retrieve audit log events belonging to the provided
                audit log event category or categories.

        Returns:
            An object representing a single page of audit log results.
        """

        start_time = coerce_iso_str(start_time)
        end_time = coerce_iso_str(end_time)
        user_id = coerce_list_str(user_id)
        event_type = coerce_list_str(event_type)
        model_id = coerce_list_str(model_id)
        category = coerce_list_str(category)
        params = {
            "startTime": start_time,
            "endTime": end_time,
            "originatingUserId": user_id,
            "eventType": event_type,
            "modelId": model_id,
            "category": category,
            "pageSize": page_size,
            "sortOrder": ("ascending" if sort_asc else "descending"),
            "previous": previous,
            "next": next,
        }
        params = {k: v for (k, v) in params.items() if v}
        offset_field = "next" if sort_asc else "previous"
        iter_requests = self.api.iterate_requests(
            method="GET",
            url=self.urls.audit_log,
            params=params,
            offset_field=offset_field,
        )
        for count, response in enumerate(iter_requests, start=1):
            parsed = AuditLogResponse.model_validate(response)
            yield parsed
            if not parsed.events:
                return
            if page_limit is not None and count >= page_limit:
                return

    def remove_user(
        self,
        user_id: str,
        replacement: str | None = None,
        *,
        descendants: bool = False,
    ) -> "UserRemoved":
        """
        Unshare a user from all enterprise workspaces, bases, and interfaces.
        If applicable, the user will also be removed from as an enterprise admin.

        See `Remove user from enterprise <https://airtable.com/developers/web/api/remove-user-from-enterprise>`__
        for more information.

        Args:
            user_id: The user ID.
            replacement: If the user is the sole owner of any workspaces, you must
                specify a replacement user ID to be added as the new owner of such
                workspaces. If the user is not the sole owner of any workspaces,
                this is optional and will be ignored if provided.
            descendants: If ``True``, removes the user from descendant enterprise accounts.
        """
        url = self.urls.remove_user(user_id)
        payload: dict[str, Any] = {"isDryRun": False}
        if replacement:
            payload["replacementOwnerId"] = replacement
        if descendants:
            payload["removeFromDescendants"] = True
        response = self.api.post(url, json=payload)
        return UserRemoved.from_api(response, self.api, context=self)

    def claim_users(
        self, users: dict[str, Literal["managed", "unmanaged"]]
    ) -> "ManageUsersResponse":
        """
        Batch manage organizations enterprise account users. This endpoint allows you
        to change a user's membership status from being unmanaged to being an
        organization member, and vice versa.

        See `Manage user membership <https://airtable.com/developers/web/api/manage-user-membership>`__
        for more information.

        Args:
            users: A ``dict`` mapping user IDs or emails to the desired state,
                either ``"managed"`` or ``"unmanaged"``.
        """
        payload = {
            "users": [
                {
                    ("email" if "@" in key else "id"): key,
                    "state": value,
                }
                for (key, value) in users.items()
            ]
        }
        response = self.api.post(self.urls.claim_users, json=payload)
        return ManageUsersResponse.from_api(response, self.api, context=self)

    def delete_users(self, emails: Iterable[str]) -> "DeleteUsersResponse":
        """
        Delete multiple users by email.

        Args:
            emails: A list or other iterable of email addresses.
        """
        response = self.api.delete(self.urls.users, params={"email": list(emails)})
        return DeleteUsersResponse.from_api(response, self.api, context=self)

    def grant_admin(self, *users: str | UserInfo) -> "ManageUsersResponse":
        """
        Grant admin access to one or more users.

        Args:
            users: One or more user IDs, email addresses, or instances of
                :class:`~pyairtable.models.schema.UserInfo`.
        """
        return self._post_admin_access("grant", users)

    def revoke_admin(self, *users: str | UserInfo) -> "ManageUsersResponse":
        """
        Revoke admin access to one or more users.

        Args:
            users: One or more user IDs, email addresses, or instances of
                :class:`~pyairtable.models.schema.UserInfo`.
        """
        return self._post_admin_access("revoke", users)

    def _post_admin_access(
        self, action: Literal["grant", "revoke"], users: Iterable[str | UserInfo]
    ) -> "ManageUsersResponse":
        response = self.api.post(
            self.urls.admin_access(action),
            json={
                "users": [
                    {"email": user_id} if "@" in user_id else {"id": user_id}
                    for user in users
                    for user_id in [user.id if isinstance(user, UserInfo) else user]
                ]
            },
        )
        return ManageUsersResponse.from_api(response, self.api, context=self)

    def create_descendant(self, name: str) -> Self:
        """
        Creates a descendant enterprise account of the enterprise account.
        Descendant enterprise accounts can only be created for root enterprise accounts
        with the Enterprise Hub feature enabled.

        See `Create descendant enterprise <https://airtable.com/developers/web/api/create-descendant-enterprise>`__.

        Args:
            name: The name to give the new account.
        """
        response = self.api.post(self.urls.descendants, json={"name": name})
        return self.__class__(self.api, response["id"])

    def move_groups(
        self,
        group_ids: Iterable[str],
        target: str | Self,
    ) -> "MoveGroupsResponse":
        """
        Move one or more user groups from the current enterprise account
        into a different enterprise account within the same organization.

        See `Move user groups <https://airtable.com/developers/web/api/move-user-groups>`__.

        Args:
            group_ids: User group IDs.
            target: The ID of the target enterprise, or an instance of :class:`~pyairtable.Enterprise`.
        """
        if isinstance(target, Enterprise):
            target = target.id
        response = self.api.post(
            self.urls.move_groups,
            json={
                "groupIds": list(group_ids),
                "targetEnterpriseAccountId": target,
            },
        )
        return MoveGroupsResponse.from_api(response, self.api, context=self)

    def move_workspaces(
        self,
        workspace_ids: Iterable[str],
        target: str | Self,
    ) -> "MoveWorkspacesResponse":
        """
        Move one or more workspaces from the current enterprise account
        into a different enterprise account within the same organization.

        See `Move workspaces <https://airtable.com/developers/web/api/move-workspaces>`__.

        Args:
            workspace_ids: The list of workspace IDs.
            target: The ID of the target enterprise, or an instance of :class:`~pyairtable.Enterprise`.
        """
        if isinstance(target, Enterprise):
            target = target.id
        response = self.api.post(
            self.urls.move_workspaces,
            json={
                "workspaceIds": list(workspace_ids),
                "targetEnterpriseAccountId": target,
            },
        )
        return MoveWorkspacesResponse.from_api(response, self.api, context=self)

    def create_workspace(self, name: str) -> "Workspace":
        """
        Creates a new workspace with the provided name within the enterprise account
        and returns the workspace ID. The requesting user must be an active effective
        admin of the enterprise account; the created workspace's owner will be the user
        who makes the request.

        See `Create workspace <https://airtable.com/developers/web/api/create-workspace>`__.

        Args:
            name: The name of the workspace to be created.

        Returns:
            The ID of the newly created workspace.
        """
        response = self.api.post(
            self.urls.create_workspace,
            json={
                "enterpriseAccountId": self.id,
                "name": name,
            },
        )
        return self.api.workspace(str(response["id"]))

    @cache_unless_forced
    def packages(
        self,
        *,
        all_enterprises: bool = False,
    ) -> list[Package]:
        """
        List all packages for the enterprise account.

        See `List packages <https://airtable.com/developers/web/api/list-enterprise-packages>`__.

        Args:
            all_enterprises: If True and the enterprise account is the root
                enterprise account, returns all packages across the entire
                enterprise grid. Defaults to False.

        Returns:
            A list of Package objects representing the enterprise packages.
        """
        params: dict[str, Any] = {}
        if all_enterprises:
            params["shouldGetAllPackagesInGrid"] = True

        response = self.api.get(self.urls.packages, params=params)
        return [
            Package.from_api(pkg, self.api, context=self)
            for pkg in response.get("packages", [])
        ]

    def package(self, package_id: str, *, force: bool = False) -> Package:
        """
        Retrieve information about a single package by ID.

        Args:
            package_id: The ID of the package to retrieve.
            force: If ``True``, forces a refresh of the cached package list.

        Returns:
            A Package object representing the enterprise package.
        """
        try:
            return next(
                package
                for package in self.packages(force=force)
                if package.id == package_id
            )
        except StopIteration:
            raise MissingRecordError(package_id)

    def create_base(
        self,
        workspace: "str | Workspace",
        name: str,
        tables: Sequence[dict[str, Any]],
    ) -> "Base":
        """
        Create a base in the given workspace.

        See https://airtable.com/developers/web/api/create-base

        Args:
            workspace: The ID of the workspace or a :class:`~pyairtable.Workspace` object.
            name: The name to give to the new base. Does not need to be unique.
            tables: A list of ``dict`` objects that conform to Airtable's
                `Table model <https://airtable.com/developers/web/api/model/table-model>`__.
        """
        if isinstance(workspace, str):
            workspace = self.api.workspace(workspace)
        return workspace.create_base(name, tables)

    def create_base_from_package(
        self,
        workspace: "str | Workspace",
        name: str,
        package_or_release: str | Package,
        *,
        description: str | None = None,
    ) -> "Base":
        """
        Create a base from an enterprise package template in the specified workspace.

        See https://airtable.com/developers/web/api/create-base-from-package-enterprise

        Args:
            workspace: The ID of the workspace or a :class:`~pyairtable.Workspace` object.
            name: The name for the new base.
            package_or_release: A :class:`~pyairtable.models.schema.Package` object,
                a package ID (``pkg...``), or a package release ID. When a package
                or package ID is given, the package's latest release is installed.
                Any other string is forwarded to the API as the release ID.
            description: Optional description for the base.

        Returns:
            The newly created Base object.

        Raises:
            MissingRecordError: If the given package ID is not found.
            InvalidParameterError: If the resolved package has no latest release.
        """
        workspace_id = workspace if isinstance(workspace, str) else workspace.id

        if isinstance(package_or_release, Package):
            package_id = package_or_release.id
            release_id = package_or_release.latest_release_id
        elif package_or_release.startswith("pkg"):
            package = self.package(package_or_release)
            package_id = package.id
            release_id = package.latest_release_id
        else:
            package_id = release_id = package_or_release

        if release_id is None:
            raise InvalidParameterError(
                f"Package {package_id!r} has no latest release to install"
            )

        payload = {
            "name": name,
            "packageReleaseId": release_id,
            "workspaceId": workspace_id,
        }
        if description is not None:
            payload["description"] = description

        response = self.api.post(self.urls.package_install(package_id), json=payload)
        return self.api.base(response["id"], validate=True, force=True)

    def access_tokens(
        self,
        *,
        resources: bool = False,
    ) -> list["PersonalAccessToken"]:
        """
        List personal access tokens for users administered by this
        enterprise account. Only supported for root (organization-level)
        enterprise accounts.

        See `List personal access tokens <https://airtable.com/developers/web/api/list-enterprise-personal-access-tokens>`__.

        Args:
            resources: If ``True``, the API will include information
                about the resources that each token can access.
        """
        params: dict[str, Any] = {}
        if resources:
            params["includeResources"] = True
        response = self.api.get(self.urls.access_tokens, params=params)
        return [
            PersonalAccessToken.from_api(token, self.api, context=self)
            for token in response.get("personalAccessTokens", [])
        ]

    def revoke_access_tokens(
        self,
        token_ids: str | Iterable[str],
    ) -> "RevokeTokensResponse":
        """
        Revoke personal access tokens for users administered by this
        enterprise account. Only supported for root (organization-level)
        enterprise accounts. The response includes both revoked tokens and
        errors, so that callers can handle partial success.

        See `Revoke personal access tokens <https://airtable.com/developers/web/api/revoke-enterprise-personal-access-tokens>`__.

        Args:
            token_ids: One or more personal access token IDs (maximum of 100).
        """
        token_ids = coerce_list_str(token_ids)
        response = self.api.post(
            self.urls.revoke_access_tokens,
            json={"tokenIds": token_ids},
        )
        return RevokeTokensResponse.from_api(response, self.api, context=self)

    def allow_ai(
        self,
        workspaces: "dict[str | Workspace, bool]",
        *,
        descendants: bool = False,
    ) -> "UpdateAiAllowlistResponse":
        """
        Add or remove workspaces from the enterprise AI allowlist
        (maximum of 10 workspaces per request). Only applicable when the
        enterprise AI workspace restriction policy is set to allow
        specified workspaces.

        See `Update workspace AI allowlist <https://airtable.com/developers/web/api/update-workspace-ai-allowlist>`__.

        Usage:
            >>> enterprise.allow_ai(
            ...     {"wspmhESAta6clCCwF": True, "wspHvvm4dAktsStZH": False}
            ... )

        Args:
            workspaces: A ``dict`` mapping workspace IDs or instances of
                :class:`~pyairtable.Workspace` to whether each workspace
                should be allowed to use AI features.
            descendants: If ``True``, changes will also be applied to
                workspaces belonging to descendant org units.
        """
        payload: dict[str, Any] = {
            "workspaces": [
                {
                    "workspaceId": ws if isinstance(ws, str) else ws.id,
                    "isAllowed": is_allowed,
                }
                for (ws, is_allowed) in workspaces.items()
            ]
        }
        if descendants:
            payload["includeDescendantWorkspaces"] = True
        response = self.api.post(self.urls.workspace_ai_allowlist, json=payload)
        return UpdateAiAllowlistResponse.from_api(response, self.api, context=self)


class UserRemoved(AirtableModel):
    """
    Returned from the `Remove user from enterprise <https://airtable.com/developers/web/api/remove-user-from-enterprise>`__
    endpoint.
    """

    was_user_removed_as_admin: bool
    shared: "UserRemoved.Shared"
    unshared: "UserRemoved.Unshared"

    class Shared(AirtableModel):
        workspaces: list["UserRemoved.Shared.Workspace"]

        class Workspace(AirtableModel):
            permission_level: str
            workspace_id: str
            workspace_name: str
            user_id: str = ""
            deleted_time: datetime | None = None
            enterprise_account_id: str | None = None

    class Unshared(AirtableModel):
        bases: list["UserRemoved.Unshared.Base"]
        interfaces: list["UserRemoved.Unshared.Interface"]
        workspaces: list["UserRemoved.Unshared.Workspace"]

        class Base(AirtableModel):
            user_id: str
            base_id: str
            base_name: str
            former_permission_level: str
            deleted_time: datetime | None = None
            enterprise_account_id: str | None = None

        class Interface(AirtableModel):
            user_id: str
            base_id: str
            interface_id: str
            interface_name: str
            former_permission_level: str
            deleted_time: datetime | None = None
            enterprise_account_id: str | None = None

        class Workspace(AirtableModel):
            user_id: str
            former_permission_level: str
            workspace_id: str
            workspace_name: str
            deleted_time: datetime | None = None
            enterprise_account_id: str | None = None


class DeleteUsersResponse(AirtableModel):
    """
    Returned from the `Delete users by email <https://airtable.com/developers/web/api/delete-users-by-email>`__
    endpoint.
    """

    deleted_users: list["DeleteUsersResponse.UserInfo"]
    errors: list["DeleteUsersResponse.Error"]

    class UserInfo(AirtableModel):
        id: str
        email: str

    class Error(AirtableModel):
        type: str
        email: str
        message: str | None = None


class ManageUsersResponse(AirtableModel):
    """
    Returned from the `Manage user membership <https://airtable.com/developers/web/api/manage-user-membership>`__,
    `Grant admin access <https://airtable.com/developers/web/api/grant-admin-access>`__, and
    `Revoke admin access <https://airtable.com/developers/web/api/revoke-admin-access>`__
    endpoints.
    """

    errors: list["ManageUsersResponse.Error"] = pydantic.Field(default_factory=list)

    class Error(AirtableModel):
        id: str | None = None
        email: str | None = None
        type: str
        message: str


class MoveError(AirtableModel):
    id: str
    type: str
    message: str


class MoveGroupsResponse(AirtableModel):
    """
    Returned by `Move user groups <https://airtable.com/developers/web/api/move-user-groups>`__.
    """

    moved_groups: list[NestedId] = pydantic.Field(default_factory=list)
    errors: list[MoveError] = pydantic.Field(default_factory=list)


class MoveWorkspacesResponse(AirtableModel):
    """
    Returned by `Move workspaces <https://airtable.com/developers/web/api/move-workspaces>`__.
    """

    moved_workspaces: list[NestedId] = pydantic.Field(default_factory=list)
    errors: list[MoveError] = pydantic.Field(default_factory=list)


class PersonalAccessToken(AirtableModel):
    """
    A personal access token, as returned by the
    `List personal access tokens <https://airtable.com/developers/web/api/list-enterprise-personal-access-tokens>`__
    endpoint.
    """

    id: str
    name: str
    state: str
    scopes: list[str] = pydantic.Field(default_factory=list)
    resource_access: "PersonalAccessToken.ResourceAccess"
    created_time: datetime
    user_id: str
    created_by_user_id: str

    class ResourceAccess(AirtableModel):
        mode: str
        enterprise_account_id: str | None = None
        resource_model_ids: list[str] | None = None


class RevokeTokensResponse(AirtableModel):
    """
    Returned by the `Revoke personal access tokens <https://airtable.com/developers/web/api/revoke-enterprise-personal-access-tokens>`__
    endpoint.
    """

    revoked_tokens: list["RevokeTokensResponse.RevokedToken"] = pydantic.Field(
        default_factory=list
    )
    errors: list["RevokeTokensResponse.Error"] = pydantic.Field(default_factory=list)

    class RevokedToken(AirtableModel):
        id: str
        user_id: str

    class Error(AirtableModel):
        type: str
        message: str
        token_id: str


class UpdateAiAllowlistResponse(AirtableModel):
    """
    Returned by the `Update workspace AI allowlist <https://airtable.com/developers/web/api/update-workspace-ai-allowlist>`__
    endpoint.
    """

    errors: list["UpdateAiAllowlistResponse.Error"] = pydantic.Field(
        default_factory=list
    )

    class Error(AirtableModel):
        type: str
        message: str
        workspace_id: str


rebuild_models(vars())
