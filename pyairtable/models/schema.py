import importlib
from datetime import datetime
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
    cast,
)

import pydantic
from typing_extensions import TypeAlias

from pyairtable.api.types import AddCollaboratorDict
from pyairtable.models._base import (
    AirtableModel,
    CanDeleteModel,
    CanUpdateModel,
    RestfulModel,
    rebuild_models,
)

if TYPE_CHECKING:
    from pyairtable import orm


FieldSpecifier: TypeAlias = Union[str, "orm.fields.AnyField"]

_T = TypeVar("_T", bound=Any)
_FL = partial(pydantic.Field, default_factory=list)
_FD = partial(pydantic.Field, default_factory=dict)


def _F(classname: str, **kwargs: Any) -> Any:
    def _create_default_from_classname() -> Any:
        this_module = importlib.import_module(__name__)
        obj: Any = this_module
        for segment in classname.split("."):
            obj = getattr(obj, segment)
        return obj()

    kwargs["default_factory"] = _create_default_from_classname
    return pydantic.Field(**kwargs)


def _find(collection: List[_T], id_or_name: str) -> _T:
    """
    For use on a collection model to find objects by either id or name.
    """
    items_by_name: Dict[str, _T] = {}

    for item in collection:
        if getattr(item, "deleted", None):
            continue
        if item.id == id_or_name:
            return item
        items_by_name[item.name] = item

    return items_by_name[id_or_name]


class _Collaborators(RestfulModel):
    """
    Mixin for use with RestfulModel subclasses that have a /collaborators endpoint.
    """

    def add_user(self, user_id: str, permission_level: str) -> None:
        """
        Add a user as a collaborator to this Airtable object.

        Args:
            user_id: The user ID.
            permission_level: |kwarg_permission_level|
        """
        self.add("user", user_id, permission_level)

    def add_group(self, group_id: str, permission_level: str) -> None:
        """
        Add a group as a collaborator to this Airtable object.

        Args:
            group_id: The group ID.
            permission_level: |kwarg_permission_level|
        """
        self.add("group", group_id, permission_level)

    def add(
        self,
        collaborator_type: str,
        collaborator_id: str,
        permission_level: str,
    ) -> None:
        """
        Add a user or group as a collaborator to this Airtable object.

        Args:
            collaborator_type: Either ``'user'`` or ``'group'``.
            collaborator_id: The user or group ID.
            permission_level: |kwarg_permission_level|
        """
        if collaborator_type not in ("user", "group"):
            raise ValueError("collaborator_type must be 'user' or 'group'")
        self.add_collaborators(
            [
                cast(
                    AddCollaboratorDict,
                    {
                        collaborator_type: {"id": collaborator_id},
                        "permissionLevel": permission_level,
                    },
                )
            ]
        )

    def add_collaborators(self, collaborators: Iterable[AddCollaboratorDict]) -> None:
        """
        Add multiple collaborators to this Airtable object.

        Args:
            collaborators: A list of ``dict`` that conform to the specification
                laid out in the `Add base collaborator <https://airtable.com/developers/web/api/add-base-collaborator#request-collaborators>`__
                API documentation.
        """
        payload = {"collaborators": list(collaborators)}
        self._api.post(f"{self._url}/collaborators", json=payload)
        self._reload()

    def update(self, collaborator_id: str, permission_level: str) -> None:
        """
        Change the permission level granted to a user or group.

        Args:
            collaborator_id: The user or group ID.
            permission_level: |kwarg_permission_level|
        """
        self._api.patch(
            f"{self._url}/collaborators/{collaborator_id}",
            json={"permissionLevel": permission_level},
        )

    def remove(self, collaborator_id: str) -> None:
        """
        Remove a user or group as a collaborator.

        Args:
            collaborator_id: The user or group ID.
        """
        self._api.delete(f"{self._url}/collaborators/{collaborator_id}")


class Bases(AirtableModel):
    """
    The list of bases visible to the API token.

    See https://airtable.com/developers/web/api/list-bases
    """

    bases: List["Bases.Info"] = _FL()

    def base(self, base_id: str) -> "Bases.Info":
        """
        Get basic information about the base with the given ID.
        """
        return _find(self.bases, base_id)

    class Info(AirtableModel):
        id: str
        name: str
        permission_level: str


class BaseCollaborators(_Collaborators, url="meta/bases/{base.id}"):
    """
    Detailed information about who can access a base.

    See https://airtable.com/developers/web/api/get-base-collaborators
    """

    id: str
    name: str
    created_time: datetime
    permission_level: str
    workspace_id: str
    interfaces: Dict[str, "BaseCollaborators.InterfaceCollaborators"] = _FD()
    group_collaborators: "BaseCollaborators.GroupCollaborators" = _F("BaseCollaborators.GroupCollaborators")  # fmt: skip
    individual_collaborators: "BaseCollaborators.IndividualCollaborators" = _F("BaseCollaborators.IndividualCollaborators")  # fmt: skip
    invite_links: "BaseCollaborators.InviteLinks" = _F("BaseCollaborators.InviteLinks")  # fmt: skip

    class InterfaceCollaborators(
        _Collaborators,
        url="meta/bases/{base.id}/interfaces/{key}",
    ):
        id: str
        name: str
        created_time: datetime
        first_publish_time: Optional[datetime] = None
        group_collaborators: List["GroupCollaborator"] = _FL()
        individual_collaborators: List["IndividualCollaborator"] = _FL()
        invite_links: List["InterfaceInviteLink"] = _FL()

    class GroupCollaborators(AirtableModel):
        via_base: List["GroupCollaborator"] = _FL(alias="baseCollaborators")
        via_workspace: List["GroupCollaborator"] = _FL(alias="workspaceCollaborators")

    class IndividualCollaborators(AirtableModel):
        via_base: List["IndividualCollaborator"] = _FL(alias="baseCollaborators")
        via_workspace: List["IndividualCollaborator"] = _FL(alias="workspaceCollaborators")  # fmt: skip

    class InviteLinks(RestfulModel, url="{base_collaborators._url}/invites"):
        via_base: List["InviteLink"] = _FL(alias="baseInviteLinks")
        via_workspace: List["WorkspaceInviteLink"] = _FL(alias="workspaceInviteLinks")  # fmt: skip


class BaseShares(AirtableModel):
    """
    Collection of shared views in a base.

    See https://airtable.com/developers/web/api/list-shares
    """

    shares: List["BaseShares.Info"]

    class Info(
        CanUpdateModel,
        CanDeleteModel,
        url="meta/bases/{base.id}/shares/{self.share_id}",
        writable=["state"],
        reload_after_save=False,
    ):
        state: str
        created_by_user_id: str
        created_time: datetime
        share_id: str
        type: str
        can_be_synced: Optional[bool] = None
        is_password_protected: bool
        block_installation_id: Optional[str] = None
        restricted_to_email_domains: List[str] = _FL()
        restricted_to_enterprise_members: bool
        view_id: Optional[str] = None
        effective_email_domain_allow_list: List[str] = _FL()

        def enable(self) -> None:
            """
            Enable the base share.
            """
            self.state = "enabled"
            self.save()

        def disable(self) -> None:
            """
            Disable the base share.
            """
            self.state = "disabled"
            self.save()


class BaseSchema(AirtableModel):
    """
    Schema of all tables within the base.

    See https://airtable.com/developers/web/api/get-base-schema

    Usage:
        >>> schema = api.base(base_id).schema()
        >>> schema.tables
        [TableSchema(...), ...]
        >>> schema.table("Table Name")
        TableSchema(
            id='tbl6jG0XedVMNxFQW',
            name='Table Name',
            primary_field_id='fld0XedVMNxFQW6jG',
            description=None,
            fields=[...],
            views=[...]
        )
    """

    tables: List["TableSchema"]

    def table(self, id_or_name: str) -> "TableSchema":
        """
        Get the schema for the table with the given ID or name.
        """
        return _find(self.tables, id_or_name)


class TableSchema(
    CanUpdateModel,
    save_null_values=False,
    writable=["name", "description", "date_dependency"],
    url="meta/bases/{base.id}/tables/{self.id}",
):
    """
    Metadata for a table.

    See https://airtable.com/developers/web/api/get-base-schema

    Usage:
        >>> schema = base.table("Table Name").schema()
        >>> schema.id
        'tbl6clmhESAtaCCwF'
        >>> schema.name
        'Table Name'

        >>> schema.fields
        [FieldSchema(...), ...]
        >>> schema().field("fld6jG0XedVMNxFQW")
        SingleLineTextFieldSchema(
            id='fld6jG0XedVMNxFQW',
            name='Name',
            type='singleLineText'
        )

        >>> schema.views
        [ViewSchema(...), ...]
        >>> schema().view("View Name")
        ViewSchema(
            id='viw6jG0XedVMNxFQW',
            name='My Grid View',
            type='grid'
        )
    """

    id: str
    name: str
    primary_field_id: str
    description: Optional[str] = None
    fields: List["FieldSchema"]
    views: List["ViewSchema"]
    date_dependency: Optional["DateDependency"] = pydantic.Field(
        alias="dateDependencySettings", default=None
    )

    def field(self, id_or_name: FieldSpecifier) -> "FieldSchema":
        """
        Get the schema for the field with the given ID or name.
        """
        from pyairtable import orm

        if isinstance(id_or_name, orm.fields.Field):
            id_or_name = id_or_name.field_name
        return _find(self.fields, id_or_name)

    def view(self, id_or_name: str) -> "ViewSchema":
        """
        Get the schema for the view with the given ID or name.
        """
        return _find(self.views, id_or_name)

    def set_date_dependency(
        self,
        start_date_field: FieldSpecifier,
        end_date_field: FieldSpecifier,
        duration_field: FieldSpecifier,
        rescheduling_mode: str,
        predecessor_field: Optional[FieldSpecifier] = None,
        skip_weekends_and_holidays: bool = False,
        holidays: Optional[List[str]] = None,
    ) -> None:
        """
        Create or replace the `date dependency settings <https://airtable.com/developers/web/api/model/date-dependency-settings>`__
        for the table. You still need to call :meth:`~TableSchema.save` to persist the changes.

        Usage:
            >>> table_schema = base.table("Table Name").schema()
            >>> table_schema.set_date_dependency(
            ...     start_date_field="Start Date",
            ...     end_date_field="End Date",
            ...     duration_field="Duration",
            ...     rescheduling_mode="flexible",
            ...     skip_weekends_and_holidays=True,
            ...     holidays=["2026-01-01", "2026-12-25"],
            ...     predecessor_field="Depends On",
            ... )
            >>> table_schema.save()

            This method also accepts ORM model fields as shorthand for those fields' IDs:

            >>> table_schema = SomeModel.meta.table.schema()
            >>> table_schema.set_date_dependency(
            ...     start_date_field=SomeModel.start_date,
            ...     end_date_field=SomeModel.end_date,
            ...     duration_field=SomeModel.duration,
            ...     rescheduling_mode="flexible",
            ... )
            >>> table_schema.save()

        Args:
            start_date_field: The field ID or name for the start date.
            end_date_field: The field ID or name for the end date.
            duration_field: The field ID or name for the duration.
            rescheduling_mode: Either "flexible", "fixed", or "none".
            skip_weekends_and_holidays: Whether to skip weekends and holidays.
            holidays: A list of holiday dates in ISO format (YYYY-MM-DD).
            predecessor_field: Optional; the field ID or name for predecessor tasks.
        """
        duration_field = self.field(duration_field).id
        start_date_field = self.field(start_date_field).id
        end_date_field = self.field(end_date_field).id
        if predecessor_field is not None:
            predecessor_field = self.field(predecessor_field).id

        self.date_dependency = TableSchema.DateDependency(
            is_enabled=True,
            duration_field_id=duration_field,
            start_date_field_id=start_date_field,
            end_date_field_id=end_date_field,
            predecessor_field_id=predecessor_field,
            rescheduling_mode=rescheduling_mode,
            should_skip_weekends_and_holidays=skip_weekends_and_holidays,
            holidays=holidays or [],
        )

    class DateDependency(AirtableModel):
        """
        Settings for date dependencies in the table.

        See https://airtable.com/developers/web/api/model/date-dependency-settings
        """

        is_enabled: bool
        duration_field_id: str
        start_date_field_id: str
        end_date_field_id: str
        predecessor_field_id: Optional[str] = None
        rescheduling_mode: str
        should_skip_weekends_and_holidays: bool
        holidays: List[str] = _FL()


class ViewSchema(CanDeleteModel, url="meta/bases/{base.id}/views/{self.id}"):
    """
    Metadata for a view.

    See https://airtable.com/developers/web/api/get-view-metadata

    Usage:
        >>> vw = table.schema().view("View name")
        >>> vw.name
        'View name'
        >>> vw.type
        'grid'
        >>> vw.delete()
    """

    id: str
    type: str
    name: str
    personal_for_user_id: Optional[str] = None
    visible_field_ids: Optional[List[str]] = None


class GroupCollaborator(AirtableModel):
    created_time: datetime
    granted_by_user_id: str
    group_id: str
    name: str
    permission_level: str


class IndividualCollaborator(AirtableModel):
    created_time: datetime
    granted_by_user_id: str
    user_id: str
    email: str
    permission_level: str


class BaseIndividualCollaborator(IndividualCollaborator):
    base_id: str


class BaseGroupCollaborator(GroupCollaborator):
    base_id: str


# URL generation for an InviteLink assumes that it is nested within
# a RestfulModel class named "InviteLink" that provides URL context.
class InviteLink(CanDeleteModel, url="{invite_links._url}/{self.id}"):
    """
    Represents an `invite link <https://airtable.com/developers/web/api/model/invite-link>`__.
    """

    id: str
    type: str
    created_time: datetime
    invited_email: Optional[str] = None
    referred_by_user_id: str
    permission_level: str
    restricted_to_email_domains: List[str] = _FL()


class BaseInviteLink(
    InviteLink,
    url="meta/bases/{self.base_id}/invites/{self.id}",
):
    """
    Represents a `base invite link <https://airtable.com/developers/web/api/model/base-invite-link>`__.
    """

    base_id: str


class WorkspaceInviteLink(
    InviteLink,
    url="meta/workspaces/{base_collaborators.workspace_id}/invites/{self.id}",
):
    """
    Represents an `invite link <https://airtable.com/developers/web/api/model/invite-link>`__
    to a workspace that was returned within a base schema.
    """


class InterfaceInviteLink(
    InviteLink,
    url="{interface_collaborators._url}/invites/{self.id}",
):
    """
    Represents an `invite link <https://airtable.com/developers/web/api/model/invite-link>`__
    to an interface that was returned within a base schema.
    """


class EnterpriseInfo(AirtableModel):
    """
    Information about groups, users, workspaces, and email domains
    associated with an enterprise account.

    See https://airtable.com/developers/web/api/get-enterprise
    """

    id: str
    created_time: datetime
    group_ids: List[str]
    user_ids: List[str]
    workspace_ids: List[str]
    email_domains: List["EnterpriseInfo.EmailDomain"]
    root_enterprise_id: str = pydantic.Field(alias="rootEnterpriseAccountId")
    descendant_enterprise_ids: List[str] = _FL(alias="descendantEnterpriseAccountIds")
    aggregated: Optional["EnterpriseInfo.AggregatedIds"] = None
    descendants: Dict[str, "EnterpriseInfo.AggregatedIds"] = _FD()

    class EmailDomain(AirtableModel):
        email_domain: str
        is_sso_required: bool

    class AggregatedIds(AirtableModel):
        group_ids: List[str] = _FL()
        user_ids: List[str] = _FL()
        workspace_ids: List[str] = _FL()


class WorkspaceCollaborators(_Collaborators, url="meta/workspaces/{self.id}"):
    """
    Detailed information about who can access a workspace.

    See https://airtable.com/developers/web/api/get-workspace-collaborators
    """

    id: str
    name: str
    created_time: datetime
    base_ids: List[str]
    restrictions: "WorkspaceCollaborators.Restrictions" = pydantic.Field(alias="workspaceRestrictions")  # fmt: skip
    group_collaborators: "WorkspaceCollaborators.GroupCollaborators" = _F("WorkspaceCollaborators.GroupCollaborators")  # fmt: skip
    individual_collaborators: "WorkspaceCollaborators.IndividualCollaborators" = _F("WorkspaceCollaborators.IndividualCollaborators")  # fmt: skip
    invite_links: "WorkspaceCollaborators.InviteLinks" = _F("WorkspaceCollaborators.InviteLinks")  # fmt: skip

    class Restrictions(
        CanUpdateModel,
        url="{workspace_collaborators._url}/updateRestrictions",
        save_method="POST",
        reload_after_save=False,
    ):
        invite_creation: str = pydantic.Field(alias="inviteCreationRestriction")
        share_creation: str = pydantic.Field(alias="shareCreationRestriction")

    class GroupCollaborators(AirtableModel):
        via_base: List["BaseGroupCollaborator"] = _FL(alias="baseCollaborators")
        via_workspace: List["GroupCollaborator"] = _FL(alias="workspaceCollaborators")

    class IndividualCollaborators(AirtableModel):
        via_base: List["BaseIndividualCollaborator"] = _FL(alias="baseCollaborators")
        via_workspace: List["IndividualCollaborator"] = _FL(
            alias="workspaceCollaborators"
        )

    class InviteLinks(RestfulModel, url="{workspace_collaborators._url}/invites"):
        via_base: List["BaseInviteLink"] = _FL(alias="baseInviteLinks")
        via_workspace: List["InviteLink"] = _FL(alias="workspaceInviteLinks")


class NestedId(AirtableModel):
    id: str


class NestedFieldId(AirtableModel):
    field_id: str


class Collaborations(AirtableModel):
    """
    The full set of collaborations granted to a user or user group.

    See https://airtable.com/developers/web/api/model/collaborations
    """

    base_collaborations: List["Collaborations.BaseCollaboration"] = _FL()
    interface_collaborations: List["Collaborations.InterfaceCollaboration"] = _FL()
    workspace_collaborations: List["Collaborations.WorkspaceCollaboration"] = _FL()

    def __bool__(self) -> bool:
        return bool(
            self.base_collaborations
            or self.interface_collaborations
            or self.workspace_collaborations
        )

    @property
    def bases(self) -> Dict[str, "Collaborations.BaseCollaboration"]:
        """
        Mapping of base IDs to collaborations, to make lookups easier.
        """
        return {c.base_id: c for c in self.base_collaborations}

    @property
    def interfaces(self) -> Dict[str, "Collaborations.InterfaceCollaboration"]:
        """
        Mapping of interface IDs to collaborations, to make lookups easier.
        """
        return {c.interface_id: c for c in self.interface_collaborations}

    @property
    def workspaces(self) -> Dict[str, "Collaborations.WorkspaceCollaboration"]:
        """
        Mapping of workspace IDs to collaborations, to make lookups easier.
        """
        return {c.workspace_id: c for c in self.workspace_collaborations}

    class BaseCollaboration(AirtableModel):
        base_id: str
        created_time: datetime
        granted_by_user_id: str
        permission_level: str

    class InterfaceCollaboration(BaseCollaboration):
        interface_id: str

    class WorkspaceCollaboration(AirtableModel):
        workspace_id: str
        created_time: datetime
        granted_by_user_id: str
        permission_level: str


class UserInfo(
    CanUpdateModel,
    CanDeleteModel,
    url="{enterprise.urls.users}/{self.id}",
    writable=["state", "email", "first_name", "last_name"],
):
    """
    Detailed information about a user.

    See https://airtable.com/developers/web/api/get-user-by-id
    """

    id: str
    name: str
    email: str
    state: str
    is_service_account: bool
    is_sso_required: bool
    is_two_factor_auth_enabled: bool
    last_activity_time: Optional[datetime] = None
    created_time: Optional[datetime] = None
    enterprise_user_type: Optional[str] = None
    invited_to_airtable_by_user_id: Optional[str] = None
    is_managed: bool = False
    is_admin: bool = False
    is_super_admin: bool = False
    groups: List[NestedId] = _FL()
    collaborations: "Collaborations" = _F("Collaborations")
    descendants: Dict[str, "UserInfo.DescendantIds"] = _FD()
    aggregated: Optional["UserInfo.AggregatedIds"] = None

    def logout(self) -> None:
        self._api.post(self._url + "/logout")

    class DescendantIds(AirtableModel):
        last_activity_time: Optional[datetime] = None
        collaborations: Optional["Collaborations"] = None
        is_admin: bool = False
        is_managed: bool = False
        groups: List[NestedId] = _FL()

    class AggregatedIds(AirtableModel):
        last_activity_time: Optional[datetime] = None
        collaborations: Optional["Collaborations"] = None
        is_admin: bool = False
        groups: List[NestedId] = _FL()


class UserGroup(AirtableModel):
    """
    Detailed information about a user group and its members.

    See https://airtable.com/developers/web/api/get-user-group
    """

    id: str
    name: str
    enterprise_account_id: str
    created_time: datetime
    updated_time: datetime
    members: List["UserGroup.Member"]
    collaborations: "Collaborations" = _F("Collaborations")
    mapped_user_license_type: Optional[str] = None

    class Member(AirtableModel):
        user_id: str
        email: str
        first_name: str
        last_name: str
        role: str
        created_time: datetime


# The data model is a bit confusing here, but it's designed for maximum reuse.
# SomethingFieldConfig contains the `type` and `options` values for each field type.
# _FieldSchemaBase contains the `id`, `name`, and `description` values.
# SomethingFieldSchema inherits from _FieldSchemaBase and SomethingFieldConfig.
# FieldConfig is a union of all available *FieldConfig classes.
# FieldSchema is a union of all available *FieldSchema classes.


class AITextFieldConfig(AirtableModel):
    """
    Field configuration for `AI text <https://airtable.com/developers/web/api/field-model#aitext>`__.
    """

    type: Literal["aiText"]
    options: "AITextFieldOptions"


class AITextFieldOptions(AirtableModel):
    prompt: List[Union[str, "AITextFieldOptions.PromptField"]] = _FL()
    referenced_field_ids: List[str] = _FL()

    class PromptField(AirtableModel):
        field: NestedFieldId


class AutoNumberFieldConfig(AirtableModel):
    """
    Field configuration for `Auto number <https://airtable.com/developers/web/api/field-model#autonumber>`__.
    """

    type: Literal["autoNumber"]


class BarcodeFieldConfig(AirtableModel):
    """
    Field configuration for `Barcode <https://airtable.com/developers/web/api/field-model#barcode>`__.
    """

    type: Literal["barcode"]


class ButtonFieldConfig(AirtableModel):
    """
    Field configuration for `Button <https://airtable.com/developers/web/api/field-model#button>`__.
    """

    type: Literal["button"]


class CheckboxFieldConfig(AirtableModel):
    """
    Field configuration for `Checkbox <https://airtable.com/developers/web/api/field-model#checkbox>`__.
    """

    type: Literal["checkbox"]
    options: "CheckboxFieldOptions"


class CheckboxFieldOptions(AirtableModel):
    color: str
    icon: str


class CountFieldConfig(AirtableModel):
    """
    Field configuration for `Count <https://airtable.com/developers/web/api/field-model#count>`__.
    """

    type: Literal["count"]
    options: "CountFieldOptions"


class CountFieldOptions(AirtableModel):
    is_valid: bool
    record_link_field_id: Optional[str] = None


class CreatedByFieldConfig(AirtableModel):
    """
    Field configuration for `Created by <https://airtable.com/developers/web/api/field-model#createdby>`__.
    """

    type: Literal["createdBy"]


class CreatedTimeFieldConfig(AirtableModel):
    """
    Field configuration for `Created time <https://airtable.com/developers/web/api/field-model#createdtime>`__.
    """

    type: Literal["createdTime"]


class CurrencyFieldConfig(AirtableModel):
    """
    Field configuration for `Currency <https://airtable.com/developers/web/api/field-model#currencynumber>`__.
    """

    type: Literal["currency"]
    options: "CurrencyFieldOptions"


class CurrencyFieldOptions(AirtableModel):
    precision: int
    symbol: str


class DateFieldConfig(AirtableModel):
    """
    Field configuration for `Date <https://airtable.com/developers/web/api/field-model#dateonly>`__.
    """

    type: Literal["date"]
    options: "DateFieldOptions"


class DateFieldOptions(AirtableModel):
    date_format: "DateTimeFieldOptions.DateFormat"


class DateTimeFieldConfig(AirtableModel):
    """
    Field configuration for `Date and time <https://airtable.com/developers/web/api/field-model#dateandtime>`__.
    """

    type: Literal["dateTime"]
    options: "DateTimeFieldOptions"


class DateTimeFieldOptions(AirtableModel):
    time_zone: str
    date_format: "DateTimeFieldOptions.DateFormat"
    time_format: "DateTimeFieldOptions.TimeFormat"

    class DateFormat(AirtableModel):
        format: str
        name: str

    class TimeFormat(AirtableModel):
        format: str
        name: str


class DurationFieldConfig(AirtableModel):
    """
    Field configuration for `Duration <https://airtable.com/developers/web/api/field-model#durationnumber>`__.
    """

    type: Literal["duration"]
    options: "DurationFieldOptions"


class DurationFieldOptions(AirtableModel):
    duration_format: str


class EmailFieldConfig(AirtableModel):
    """
    Field configuration for `Email <https://airtable.com/developers/web/api/field-model#email>`__.
    """

    type: Literal["email"]


class ExternalSyncSourceFieldConfig(AirtableModel):
    """
    Field configuration for `Sync source <https://airtable.com/developers/web/api/field-model#syncsource>`__.
    """

    type: Literal["externalSyncSource"]
    options: "SingleSelectFieldOptions"


class FormulaFieldConfig(AirtableModel):
    """
    Field configuration for `Formula <https://airtable.com/developers/web/api/field-model#formula>`__.
    """

    type: Literal["formula"]
    options: "FormulaFieldOptions"


class FormulaFieldOptions(AirtableModel):
    formula: str
    is_valid: bool
    referenced_field_ids: Optional[List[str]] = None
    result: Optional["FieldConfig"] = None


class LastModifiedByFieldConfig(AirtableModel):
    """
    Field configuration for `Last modified by <https://airtable.com/developers/web/api/field-model#lastmodifiedby>`__.
    """

    type: Literal["lastModifiedBy"]


class LastModifiedTimeFieldConfig(AirtableModel):
    """
    Field configuration for `Last modified time <https://airtable.com/developers/web/api/field-model#lastmodifiedtime>`__.
    """

    type: Literal["lastModifiedTime"]
    options: "LastModifiedTimeFieldOptions"


class LastModifiedTimeFieldOptions(AirtableModel):
    is_valid: bool
    referenced_field_ids: Optional[List[str]] = None
    result: Optional[Union["DateFieldConfig", "DateTimeFieldConfig"]] = None


class ManualSortFieldConfig(AirtableModel):
    """
    Field configuration for ``manualSort`` field type (not documented).
    """

    type: Literal["manualSort"]


class MultilineTextFieldConfig(AirtableModel):
    """
    Field configuration for `Long text <https://airtable.com/developers/web/api/field-model#multilinetext>`__.
    """

    type: Literal["multilineText"]


class MultipleAttachmentsFieldConfig(AirtableModel):
    """
    Field configuration for `Attachments <https://airtable.com/developers/web/api/field-model#multipleattachment>`__.
    """

    type: Literal["multipleAttachments"]
    options: "MultipleAttachmentsFieldOptions"


class MultipleAttachmentsFieldOptions(AirtableModel):
    """
    Field configuration for `Attachments <https://airtable.com/developers/web/api/field-model#multipleattachment>`__.
    """

    is_reversed: bool


class MultipleCollaboratorsFieldConfig(AirtableModel):
    """
    Field configuration for `Multiple Collaborators <https://airtable.com/developers/web/api/field-model#multicollaborator>`__.
    """

    type: Literal["multipleCollaborators"]


class MultipleLookupValuesFieldConfig(AirtableModel):
    """
    Field configuration for `Lookup <https://airtable.com/developers/web/api/field-model#lookup>__`.
    """

    type: Literal["multipleLookupValues"]
    options: "MultipleLookupValuesFieldOptions"


class MultipleLookupValuesFieldOptions(AirtableModel):
    is_valid: bool
    field_id_in_linked_table: Optional[str] = None
    record_link_field_id: Optional[str] = None
    result: Optional["FieldConfig"] = None


class MultipleRecordLinksFieldConfig(AirtableModel):
    """
    Field configuration for `Link to another record <https://airtable.com/developers/web/api/field-model#foreignkey>__`.
    """

    type: Literal["multipleRecordLinks"]
    options: "MultipleRecordLinksFieldOptions"


class MultipleRecordLinksFieldOptions(AirtableModel):
    is_reversed: bool
    linked_table_id: str
    prefers_single_record_link: bool
    inverse_link_field_id: Optional[str] = None
    view_id_for_record_selection: Optional[str] = None


class MultipleSelectsFieldConfig(AirtableModel):
    """
    Field configuration for `Multiple select <https://airtable.com/developers/web/api/field-model#multiselect>`__.
    """

    type: Literal["multipleSelects"]
    options: "SingleSelectFieldOptions"


class NumberFieldConfig(AirtableModel):
    """
    Field configuration for `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__.
    """

    type: Literal["number"]
    options: "NumberFieldOptions"


class NumberFieldOptions(AirtableModel):
    precision: int


class PercentFieldConfig(AirtableModel):
    """
    Field configuration for `Percent <https://airtable.com/developers/web/api/field-model#percentnumber>`__.
    """

    type: Literal["percent"]
    options: "NumberFieldOptions"


class PhoneNumberFieldConfig(AirtableModel):
    """
    Field configuration for `Phone <https://airtable.com/developers/web/api/field-model#phone>`__.
    """

    type: Literal["phoneNumber"]


class RatingFieldConfig(AirtableModel):
    """
    Field configuration for `Rating <https://airtable.com/developers/web/api/field-model#rating>`__.
    """

    type: Literal["rating"]
    options: "RatingFieldOptions"


class RatingFieldOptions(AirtableModel):
    color: str
    icon: str
    max: int


class RichTextFieldConfig(AirtableModel):
    """
    Field configuration for `Rich text <https://airtable.com/developers/web/api/field-model#rich-text>`__.
    """

    type: Literal["richText"]


class RollupFieldConfig(AirtableModel):
    """
    Field configuration for `Rollup <https://airtable.com/developers/web/api/field-model#rollup>__`.
    """

    type: Literal["rollup"]
    options: "RollupFieldOptions"


class RollupFieldOptions(AirtableModel):
    field_id_in_linked_table: Optional[str] = None
    is_valid: bool
    record_link_field_id: Optional[str] = None
    referenced_field_ids: Optional[List[str]] = None
    result: Optional["FieldConfig"] = None


class SingleCollaboratorFieldConfig(AirtableModel):
    """
    Field configuration for `Collaborator <https://airtable.com/developers/web/api/field-model#collaborator>`__.
    """

    type: Literal["singleCollaborator"]


class SingleLineTextFieldConfig(AirtableModel):
    """
    Field configuration for `Single line text <https://airtable.com/developers/web/api/field-model#simpletext>`__.
    """

    type: Literal["singleLineText"]


class SingleSelectFieldConfig(AirtableModel):
    """
    Field configuration for `Single select <https://airtable.com/developers/web/api/field-model#select>`__.
    """

    type: Literal["singleSelect"]
    options: "SingleSelectFieldOptions"


class SingleSelectFieldOptions(AirtableModel):
    choices: List["SingleSelectFieldOptions.Choice"]

    class Choice(AirtableModel):
        id: str
        name: str
        color: Optional[str] = None


class UrlFieldConfig(AirtableModel):
    """
    Field configuration for `Url <https://airtable.com/developers/web/api/field-model#urltext>`__.
    """

    type: Literal["url"]


class UnknownFieldConfig(AirtableModel):
    """
    Field configuration class used as a fallback for unrecognized types.
    This ensures we don't raise pydantic.ValidationError if Airtable adds new types.
    """

    type: str
    options: Optional[Dict[str, Any]] = None


class _FieldSchemaBase(
    CanUpdateModel,
    save_null_values=False,
    writable=["name", "description"],
    url="meta/bases/{base.id}/tables/{table_schema.id}/fields/{self.id}",
):
    id: str
    name: str
    description: Optional[str] = None


# This section is auto-generated so that FieldSchema and FieldConfig are kept aligned.
# See .pre-commit-config.yaml, or just run `tox -e pre-commit` to refresh it.
# fmt: off
r"""[[[cog]]]

import re
with open(cog.inFile) as fp:
    field_types = re.findall(
        r"class (\w+Field)Config\(.*?\):(?:\n    \"{3}(.*?)\"{3})?",
        fp.read(),
        re.MULTILINE + re.DOTALL
    )

cog.out("\n\n")

cog.outl("FieldConfig: TypeAlias = Union[")
for fld, _ in field_types:
    cog.outl(f"    {fld}Config,")
cog.outl("]")
cog.out("\n\n")

for fld, doc in field_types:
    cog.out(f"class {fld}Schema(_FieldSchemaBase, {fld}Config):\n    ")
    if doc:
        doc = doc.replace('ield configuration', 'ield schema')
        cog.outl("\"\"\"" + doc + "\"\"\"")
    else:
        cog.outl("pass")
    cog.out("\n\n")

cog.outl("FieldSchema: TypeAlias = Union[")
for fld, _ in field_types:
    cog.outl(f"    {fld}Schema,")
cog.outl("]")

[[[out]]]"""


FieldConfig: TypeAlias = Union[
    AITextFieldConfig,
    AutoNumberFieldConfig,
    BarcodeFieldConfig,
    ButtonFieldConfig,
    CheckboxFieldConfig,
    CountFieldConfig,
    CreatedByFieldConfig,
    CreatedTimeFieldConfig,
    CurrencyFieldConfig,
    DateFieldConfig,
    DateTimeFieldConfig,
    DurationFieldConfig,
    EmailFieldConfig,
    ExternalSyncSourceFieldConfig,
    FormulaFieldConfig,
    LastModifiedByFieldConfig,
    LastModifiedTimeFieldConfig,
    ManualSortFieldConfig,
    MultilineTextFieldConfig,
    MultipleAttachmentsFieldConfig,
    MultipleCollaboratorsFieldConfig,
    MultipleLookupValuesFieldConfig,
    MultipleRecordLinksFieldConfig,
    MultipleSelectsFieldConfig,
    NumberFieldConfig,
    PercentFieldConfig,
    PhoneNumberFieldConfig,
    RatingFieldConfig,
    RichTextFieldConfig,
    RollupFieldConfig,
    SingleCollaboratorFieldConfig,
    SingleLineTextFieldConfig,
    SingleSelectFieldConfig,
    UrlFieldConfig,
    UnknownFieldConfig,
]


class AITextFieldSchema(_FieldSchemaBase, AITextFieldConfig):
    """
    Field schema for `AI text <https://airtable.com/developers/web/api/field-model#aitext>`__.
    """


class AutoNumberFieldSchema(_FieldSchemaBase, AutoNumberFieldConfig):
    """
    Field schema for `Auto number <https://airtable.com/developers/web/api/field-model#autonumber>`__.
    """


class BarcodeFieldSchema(_FieldSchemaBase, BarcodeFieldConfig):
    """
    Field schema for `Barcode <https://airtable.com/developers/web/api/field-model#barcode>`__.
    """


class ButtonFieldSchema(_FieldSchemaBase, ButtonFieldConfig):
    """
    Field schema for `Button <https://airtable.com/developers/web/api/field-model#button>`__.
    """


class CheckboxFieldSchema(_FieldSchemaBase, CheckboxFieldConfig):
    """
    Field schema for `Checkbox <https://airtable.com/developers/web/api/field-model#checkbox>`__.
    """


class CountFieldSchema(_FieldSchemaBase, CountFieldConfig):
    """
    Field schema for `Count <https://airtable.com/developers/web/api/field-model#count>`__.
    """


class CreatedByFieldSchema(_FieldSchemaBase, CreatedByFieldConfig):
    """
    Field schema for `Created by <https://airtable.com/developers/web/api/field-model#createdby>`__.
    """


class CreatedTimeFieldSchema(_FieldSchemaBase, CreatedTimeFieldConfig):
    """
    Field schema for `Created time <https://airtable.com/developers/web/api/field-model#createdtime>`__.
    """


class CurrencyFieldSchema(_FieldSchemaBase, CurrencyFieldConfig):
    """
    Field schema for `Currency <https://airtable.com/developers/web/api/field-model#currencynumber>`__.
    """


class DateFieldSchema(_FieldSchemaBase, DateFieldConfig):
    """
    Field schema for `Date <https://airtable.com/developers/web/api/field-model#dateonly>`__.
    """


class DateTimeFieldSchema(_FieldSchemaBase, DateTimeFieldConfig):
    """
    Field schema for `Date and time <https://airtable.com/developers/web/api/field-model#dateandtime>`__.
    """


class DurationFieldSchema(_FieldSchemaBase, DurationFieldConfig):
    """
    Field schema for `Duration <https://airtable.com/developers/web/api/field-model#durationnumber>`__.
    """


class EmailFieldSchema(_FieldSchemaBase, EmailFieldConfig):
    """
    Field schema for `Email <https://airtable.com/developers/web/api/field-model#email>`__.
    """


class ExternalSyncSourceFieldSchema(_FieldSchemaBase, ExternalSyncSourceFieldConfig):
    """
    Field schema for `Sync source <https://airtable.com/developers/web/api/field-model#syncsource>`__.
    """


class FormulaFieldSchema(_FieldSchemaBase, FormulaFieldConfig):
    """
    Field schema for `Formula <https://airtable.com/developers/web/api/field-model#formula>`__.
    """


class LastModifiedByFieldSchema(_FieldSchemaBase, LastModifiedByFieldConfig):
    """
    Field schema for `Last modified by <https://airtable.com/developers/web/api/field-model#lastmodifiedby>`__.
    """


class LastModifiedTimeFieldSchema(_FieldSchemaBase, LastModifiedTimeFieldConfig):
    """
    Field schema for `Last modified time <https://airtable.com/developers/web/api/field-model#lastmodifiedtime>`__.
    """


class ManualSortFieldSchema(_FieldSchemaBase, ManualSortFieldConfig):
    """
    Field schema for ``manualSort`` field type (not documented).
    """


class MultilineTextFieldSchema(_FieldSchemaBase, MultilineTextFieldConfig):
    """
    Field schema for `Long text <https://airtable.com/developers/web/api/field-model#multilinetext>`__.
    """


class MultipleAttachmentsFieldSchema(_FieldSchemaBase, MultipleAttachmentsFieldConfig):
    """
    Field schema for `Attachments <https://airtable.com/developers/web/api/field-model#multipleattachment>`__.
    """


class MultipleCollaboratorsFieldSchema(_FieldSchemaBase, MultipleCollaboratorsFieldConfig):
    """
    Field schema for `Multiple Collaborators <https://airtable.com/developers/web/api/field-model#multicollaborator>`__.
    """


class MultipleLookupValuesFieldSchema(_FieldSchemaBase, MultipleLookupValuesFieldConfig):
    """
    Field schema for `Lookup <https://airtable.com/developers/web/api/field-model#lookup>__`.
    """


class MultipleRecordLinksFieldSchema(_FieldSchemaBase, MultipleRecordLinksFieldConfig):
    """
    Field schema for `Link to another record <https://airtable.com/developers/web/api/field-model#foreignkey>__`.
    """


class MultipleSelectsFieldSchema(_FieldSchemaBase, MultipleSelectsFieldConfig):
    """
    Field schema for `Multiple select <https://airtable.com/developers/web/api/field-model#multiselect>`__.
    """


class NumberFieldSchema(_FieldSchemaBase, NumberFieldConfig):
    """
    Field schema for `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__.
    """


class PercentFieldSchema(_FieldSchemaBase, PercentFieldConfig):
    """
    Field schema for `Percent <https://airtable.com/developers/web/api/field-model#percentnumber>`__.
    """


class PhoneNumberFieldSchema(_FieldSchemaBase, PhoneNumberFieldConfig):
    """
    Field schema for `Phone <https://airtable.com/developers/web/api/field-model#phone>`__.
    """


class RatingFieldSchema(_FieldSchemaBase, RatingFieldConfig):
    """
    Field schema for `Rating <https://airtable.com/developers/web/api/field-model#rating>`__.
    """


class RichTextFieldSchema(_FieldSchemaBase, RichTextFieldConfig):
    """
    Field schema for `Rich text <https://airtable.com/developers/web/api/field-model#rich-text>`__.
    """


class RollupFieldSchema(_FieldSchemaBase, RollupFieldConfig):
    """
    Field schema for `Rollup <https://airtable.com/developers/web/api/field-model#rollup>__`.
    """


class SingleCollaboratorFieldSchema(_FieldSchemaBase, SingleCollaboratorFieldConfig):
    """
    Field schema for `Collaborator <https://airtable.com/developers/web/api/field-model#collaborator>`__.
    """


class SingleLineTextFieldSchema(_FieldSchemaBase, SingleLineTextFieldConfig):
    """
    Field schema for `Single line text <https://airtable.com/developers/web/api/field-model#simpletext>`__.
    """


class SingleSelectFieldSchema(_FieldSchemaBase, SingleSelectFieldConfig):
    """
    Field schema for `Single select <https://airtable.com/developers/web/api/field-model#select>`__.
    """


class UrlFieldSchema(_FieldSchemaBase, UrlFieldConfig):
    """
    Field schema for `Url <https://airtable.com/developers/web/api/field-model#urltext>`__.
    """


class UnknownFieldSchema(_FieldSchemaBase, UnknownFieldConfig):
    """
    Field schema class used as a fallback for unrecognized types.
    This ensures we don't raise pydantic.ValidationError if Airtable adds new types.
    """


FieldSchema: TypeAlias = Union[
    AITextFieldSchema,
    AutoNumberFieldSchema,
    BarcodeFieldSchema,
    ButtonFieldSchema,
    CheckboxFieldSchema,
    CountFieldSchema,
    CreatedByFieldSchema,
    CreatedTimeFieldSchema,
    CurrencyFieldSchema,
    DateFieldSchema,
    DateTimeFieldSchema,
    DurationFieldSchema,
    EmailFieldSchema,
    ExternalSyncSourceFieldSchema,
    FormulaFieldSchema,
    LastModifiedByFieldSchema,
    LastModifiedTimeFieldSchema,
    ManualSortFieldSchema,
    MultilineTextFieldSchema,
    MultipleAttachmentsFieldSchema,
    MultipleCollaboratorsFieldSchema,
    MultipleLookupValuesFieldSchema,
    MultipleRecordLinksFieldSchema,
    MultipleSelectsFieldSchema,
    NumberFieldSchema,
    PercentFieldSchema,
    PhoneNumberFieldSchema,
    RatingFieldSchema,
    RichTextFieldSchema,
    RollupFieldSchema,
    SingleCollaboratorFieldSchema,
    SingleLineTextFieldSchema,
    SingleSelectFieldSchema,
    UrlFieldSchema,
    UnknownFieldSchema,
]
# [[[end]]] (checksum: ca159bc8c76b1d15a2a57f0e76fb8911)
# fmt: on


# Shortcut to allow parsing unions, which is not possible otherwise in Pydantic v1.
# See https://github.com/pydantic/pydantic/discussions/4950
class _HasFieldSchema(AirtableModel):
    field_schema: FieldSchema


def parse_field_schema(obj: Dict[str, Any]) -> FieldSchema:
    """
    Given a ``dict`` representing a field schema,
    parse it into the appropriate FieldSchema subclass.
    """
    return _HasFieldSchema.model_validate({"field_schema": obj}).field_schema


rebuild_models(vars())
