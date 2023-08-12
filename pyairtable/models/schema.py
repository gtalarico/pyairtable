from functools import partial
from typing import Any, Dict, List, Literal, Optional, TypeVar, Union

from typing_extensions import TypeAlias

from pyairtable._compat import pydantic

from ._base import AirtableModel, update_forward_refs

PermissionLevel: TypeAlias = Literal[
    "none", "read", "comment", "edit", "create", "owner"
]

_T = TypeVar("_T", bound=Any)
_FL = partial(pydantic.Field, default_factory=list)
_FD = partial(pydantic.Field, default_factory=dict)


def _find(collection: List[_T], id_or_name: str) -> _T:
    """
    For use on a collection model to find objects by either id or name.
    """
    items_by_name: Dict[str, _T] = {}

    for item in collection:
        if item.id == id_or_name:
            return item
        items_by_name[item.name] = item

    return items_by_name[id_or_name]


class Bases(AirtableModel):
    """
    See https://airtable.com/developers/web/api/list-bases
    """

    bases: List["Bases.Info"] = _FL()

    def base(self, base_id: str) -> "Bases.Info":
        """
        Returns basic information about the base with the given ID.
        """
        return _find(self.bases, base_id)

    class Info(AirtableModel):
        id: str
        name: str
        permission_level: PermissionLevel


class BaseInfo(AirtableModel):
    """
    See https://airtable.com/developers/web/api/get-base-collaborators
    """

    id: str
    name: str
    permission_level: PermissionLevel
    workspace_id: str
    interfaces: Dict[str, "BaseInfo.InterfaceCollaborators"] = _FD()
    group_collaborators: Optional["BaseInfo.GroupCollaborators"]
    individual_collaborators: Optional["BaseInfo.IndividualCollaborators"]
    invite_links: Optional["BaseInfo.InviteLinks"]

    class InterfaceCollaborators(AirtableModel):
        created_time: str
        group_collaborators: List["GroupCollaborator"] = _FL()
        individual_collaborators: List["IndividualCollaborator"] = _FL()
        invite_links: List["InviteLink"] = _FL()

    class GroupCollaborators(AirtableModel):
        via_base: List["GroupCollaborator"] = _FL(alias="baseCollaborators")
        via_workspace: List["GroupCollaborator"] = _FL(alias="workspaceCollaborators")

    class IndividualCollaborators(AirtableModel):
        via_base: List["IndividualCollaborator"] = _FL(alias="baseCollaborators")
        via_workspace: List["IndividualCollaborator"] = _FL(
            alias="workspaceCollaborators"
        )

    class InviteLinks(AirtableModel):
        base_invite_links: List["InviteLink"] = _FL()
        workspace_invite_links: List["InviteLink"] = _FL()


class BaseSchema(AirtableModel):
    """
    See https://airtable.com/developers/web/api/get-base-schema
    """

    tables: List["TableSchema"]

    def table(self, id_or_name: str) -> "TableSchema":
        """
        Returns the schema for the table with the given ID or name.
        """
        return _find(self.tables, id_or_name)


class TableSchema(AirtableModel):
    """
    See https://airtable.com/developers/web/api/get-base-schema
    """

    id: str
    name: str
    primary_field_id: str
    description: Optional[str]
    fields: List["FieldSchema"]
    views: List["ViewSchema"]

    def field(self, id_or_name: str) -> "FieldSchema":
        """
        Returns the schema for the field with the given ID or name.
        """
        return _find(self.fields, id_or_name)

    def view(self, id_or_name: str) -> "ViewSchema":
        """
        Returns the schema for the view with the given ID or name.
        """
        return _find(self.views, id_or_name)


class ViewSchema(AirtableModel):
    """
    See https://airtable.com/developers/web/api/get-view-metadata
    """

    id: str
    type: str
    name: str
    personal_for_user_id: Optional[str]
    visible_field_ids: Optional[List[str]]


class GroupCollaborator(AirtableModel):
    created_time: str
    granted_by_user_id: str
    group_id: str
    name: str
    permission_level: PermissionLevel


class IndividualCollaborator(AirtableModel):
    created_time: str
    granted_by_user_id: str
    user_id: str
    email: str
    permission_level: PermissionLevel


class InviteLink(AirtableModel):
    id: str
    type: str
    created_time: str
    invited_email: Optional[str]
    referred_by_user_id: str
    permission_level: PermissionLevel
    restricted_to_email_domains: List[str] = _FL()


class BaseIndividualCollaborator(IndividualCollaborator):
    base_id: str


class BaseGroupCollaborator(GroupCollaborator):
    base_id: str


class BaseInviteLink(InviteLink):
    base_id: str


class EnterpriseInfo(AirtableModel):
    id: str
    created_time: str
    group_ids: List[str]
    user_ids: List[str]
    workspace_ids: List[str]
    email_domains: List["EnterpriseInfo.EmailDomain"]

    class EmailDomain(AirtableModel):
        email_domain: str
        is_sso_required: bool


class WorkspaceInfo(AirtableModel):
    id: str
    name: str
    created_time: str
    base_ids: List[str]
    restrictions: "WorkspaceInfo.Restrictions" = pydantic.Field(alias="workspaceRestrictions")  # fmt: skip
    group_collaborators: Optional["WorkspaceInfo.GroupCollaborators"] = None
    individual_collaborators: Optional["WorkspaceInfo.IndividualCollaborators"] = None
    invite_links: Optional["WorkspaceInfo.InviteLinks"] = None

    class Restrictions(AirtableModel):
        invite_creation: str = pydantic.Field(alias="inviteCreationRestriction")
        share_creation: str = pydantic.Field(alias="shareCreationRestriction")

    class GroupCollaborators(AirtableModel):
        base_collaborators: List["BaseGroupCollaborator"]
        workspace_collaborators: List["GroupCollaborator"]

    class IndividualCollaborators(AirtableModel):
        base_collaborators: List["BaseIndividualCollaborator"]
        workspace_collaborators: List["IndividualCollaborator"]

    class InviteLinks(AirtableModel):
        base_invite_links: List["BaseInviteLink"]
        workspace_invite_links: List["InviteLink"]


class _NestedId(AirtableModel):
    id: str


class UserInfo(AirtableModel):
    id: str
    name: str
    email: str
    state: str
    created_time: Optional[str]
    invited_to_airtable_by_user_id: Optional[str]
    last_activity_time: Optional[str]
    is_managed_user: bool
    groups: List[_NestedId] = pydantic.Field(default_factory=list)


class GroupInfo(AirtableModel):
    id: str
    name: str
    enterprise_account_id: str
    created_time: str
    updated_time: str
    members: List["GroupInfo.GroupMember"]

    class GroupMember(AirtableModel):
        user_id: str
        email: str
        first_name: str
        last_name: str
        role: str
        created_time: str


# The data model is a bit confusing here, but it's designed for maximum reuse.
# SomethingFieldConfig contains the `type` and `options` values for each field type.
# _FieldSchemaBase contains the `id`, `name`, and `description` values.
# SomethingFieldSchema inherits from _FieldSchemaBase and SomethingFieldConfig.
# FieldConfig is a union of all available *FieldConfig classes.
# FieldSchema is a union of all available *FieldSchema classes.


class AutoNumberFieldConfig(AirtableModel):
    type: Literal["autoNumber"]


class BarcodeFieldConfig(AirtableModel):
    type: Literal["barcode"]


class ButtonFieldConfig(AirtableModel):
    type: Literal["button"]


class CheckboxFieldConfig(AirtableModel):
    type: Literal["checkbox"]
    options: Optional["CheckboxFieldConfig.Options"]

    class Options(AirtableModel):
        color: str
        icon: str


class CountFieldConfig(AirtableModel):
    type: Literal["count"]
    options: Optional["CountFieldConfig.Options"]

    class Options(AirtableModel):
        is_valid: bool
        record_link_field_id: Optional[str]


class CreatedByFieldConfig(AirtableModel):
    type: Literal["createdBy"]


class CreatedTimeFieldConfig(AirtableModel):
    type: Literal["createdTime"]


class CurrencyFieldConfig(AirtableModel):
    type: Literal["currency"]
    options: "CurrencyFieldConfig.Options"

    class Options(AirtableModel):
        precision: int
        symbol: str


class DateFieldConfig(AirtableModel):
    type: Literal["date"]
    options: "DateFieldConfig.Options"

    class Options(AirtableModel):
        date_format: "DateTimeFieldConfig.Options.DateFormat"


class DateTimeFieldConfig(AirtableModel):
    type: Literal["dateTime"]
    options: "DateTimeFieldConfig.Options"

    class Options(AirtableModel):
        time_zone: str
        date_format: "DateTimeFieldConfig.Options.DateFormat"
        time_format: "DateTimeFieldConfig.Options.TimeFormat"

        class DateFormat(AirtableModel):
            format: str
            name: str

        class TimeFormat(AirtableModel):
            format: str
            name: str


class DurationFieldConfig(AirtableModel):
    type: Literal["duration"]
    options: Optional["DurationFieldConfig.Options"]

    class Options(AirtableModel):
        duration_format: str


class EmailFieldConfig(AirtableModel):
    type: Literal["email"]


class ExternalSyncSourceFieldConfig(AirtableModel):
    type: Literal["externalSyncSource"]
    options: Optional["SingleSelectFieldConfig.Options"]


class FormulaFieldConfig(AirtableModel):
    type: Literal["formula"]
    options: Optional["FormulaFieldConfig.Options"]

    class Options(AirtableModel):
        formula: str
        is_valid: bool
        referenced_field_ids: Optional[List[str]]
        result: Optional["FieldConfig"]


class LastModifiedByFieldConfig(AirtableModel):
    type: Literal["lastModifiedBy"]


class LastModifiedTimeFieldConfig(AirtableModel):
    type: Literal["lastModifiedTime"]
    options: Optional["LastModifiedTimeFieldConfig.Options"]

    class Options(AirtableModel):
        is_valid: bool
        referenced_field_ids: Optional[List[str]]
        result: Optional[Union["DateFieldConfig", "DateTimeFieldConfig"]]


class MultilineTextFieldConfig(AirtableModel):
    type: Literal["multilineText"]


class MultipleAttachmentsFieldConfig(AirtableModel):
    type: Literal["multipleAttachments"]
    options: Optional["MultipleAttachmentsFieldConfig.Options"]

    class Options(AirtableModel):
        is_reversed: bool


class MultipleCollaboratorsFieldConfig(AirtableModel):
    type: Literal["multipleCollaborators"]


class MultipleLookupValuesFieldConfig(AirtableModel):
    type: Literal["multipleLookupValues"]
    options: Optional["MultipleLookupValuesFieldConfig.Options"]

    class Options(AirtableModel):
        field_id_in_linked_table: Optional[str]
        is_valid: bool
        record_link_field_id: Optional[str]
        result: Optional["FieldConfig"]


class MultipleRecordLinksFieldConfig(AirtableModel):
    type: Literal["multipleRecordLinks"]
    options: Optional["MultipleRecordLinksFieldConfig.Options"]

    class Options(AirtableModel):
        is_reversed: bool
        linked_table_id: str
        prefers_single_record_link: bool
        inverse_link_field_id: Optional[str]
        view_id_for_record_selection: Optional[str]


class MultipleSelectsFieldConfig(AirtableModel):
    type: Literal["multipleSelects"]
    options: Optional["SingleSelectFieldConfig.Options"]


class NumberFieldConfig(AirtableModel):
    type: Literal["number"]
    options: Optional["NumberFieldConfig.Options"]

    class Options(AirtableModel):
        precision: int


class PercentFieldConfig(AirtableModel):
    type: Literal["percent"]
    options: Optional["NumberFieldConfig.Options"]


class PhoneNumberFieldConfig(AirtableModel):
    type: Literal["phoneNumber"]


class RatingFieldConfig(AirtableModel):
    type: Literal["rating"]
    options: Optional["RatingFieldConfig.Options"]

    class Options(AirtableModel):
        color: str
        icon: str
        max: int


class RichTextFieldConfig(AirtableModel):
    type: Literal["richText"]


class RollupFieldConfig(AirtableModel):
    type: Literal["rollup"]
    options: Optional["RollupFieldConfig.Options"]

    class Options(AirtableModel):
        field_id_in_linked_table: Optional[str]
        is_valid: bool
        record_link_field_id: Optional[str]
        referenced_field_ids: Optional[List[str]]
        result: Optional["FieldConfig"]


class SingleCollaboratorFieldConfig(AirtableModel):
    type: Literal["singleCollaborator"]


class SingleLineTextFieldConfig(AirtableModel):
    type: Literal["singleLineText"]


class SingleSelectFieldConfig(AirtableModel):
    type: Literal["singleSelect"]
    options: Optional["SingleSelectFieldConfig.Options"]

    class Options(AirtableModel):
        choices: List["SingleSelectFieldConfig.Choice"]

    class Choice(AirtableModel):
        id: str
        name: str
        color: Optional[str]


class UrlFieldConfig(AirtableModel):
    type: Literal["url"]


class UnknownFieldConfig(AirtableModel):
    """
    Fallback field configuration class so that the library doesn't crash
    with a ValidationError if Airtable adds new types of fields in the future.
    """

    type: str
    options: Optional[Dict[Any, Any]]


class _FieldSchemaBase(AirtableModel):
    id: str
    name: str
    description: Optional[str]


# This section is auto-generated so that FieldSchema and FieldConfig are kept aligned.
# See .pre-commit-config.yaml, or just run `tox -e pre-commit` to refresh it.
# fmt: off
r"""[[[cog]]]

import re
with open(cog.inFile) as fp:
    field_types = re.findall(r"class (\w+Field)Config\(", fp.read())

cog.outl("FieldConfig: TypeAlias = Union[")
for fld in field_types:
    cog.outl(f"    {fld}Config,")
cog.outl("]")
cog.out("\n\n")

for fld in field_types:
    cog.outl(f"class {fld}Schema(_FieldSchemaBase, {fld}Config): pass  # noqa")
cog.out("\n\n")

cog.outl("FieldSchema: TypeAlias = Union[")
for fld in field_types:
    cog.outl(f"    {fld}Schema,")
cog.outl("]")

[[[out]]]"""
FieldConfig: TypeAlias = Union[
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


class AutoNumberFieldSchema(_FieldSchemaBase, AutoNumberFieldConfig): pass  # noqa
class BarcodeFieldSchema(_FieldSchemaBase, BarcodeFieldConfig): pass  # noqa
class ButtonFieldSchema(_FieldSchemaBase, ButtonFieldConfig): pass  # noqa
class CheckboxFieldSchema(_FieldSchemaBase, CheckboxFieldConfig): pass  # noqa
class CountFieldSchema(_FieldSchemaBase, CountFieldConfig): pass  # noqa
class CreatedByFieldSchema(_FieldSchemaBase, CreatedByFieldConfig): pass  # noqa
class CreatedTimeFieldSchema(_FieldSchemaBase, CreatedTimeFieldConfig): pass  # noqa
class CurrencyFieldSchema(_FieldSchemaBase, CurrencyFieldConfig): pass  # noqa
class DateFieldSchema(_FieldSchemaBase, DateFieldConfig): pass  # noqa
class DateTimeFieldSchema(_FieldSchemaBase, DateTimeFieldConfig): pass  # noqa
class DurationFieldSchema(_FieldSchemaBase, DurationFieldConfig): pass  # noqa
class EmailFieldSchema(_FieldSchemaBase, EmailFieldConfig): pass  # noqa
class ExternalSyncSourceFieldSchema(_FieldSchemaBase, ExternalSyncSourceFieldConfig): pass  # noqa
class FormulaFieldSchema(_FieldSchemaBase, FormulaFieldConfig): pass  # noqa
class LastModifiedByFieldSchema(_FieldSchemaBase, LastModifiedByFieldConfig): pass  # noqa
class LastModifiedTimeFieldSchema(_FieldSchemaBase, LastModifiedTimeFieldConfig): pass  # noqa
class MultilineTextFieldSchema(_FieldSchemaBase, MultilineTextFieldConfig): pass  # noqa
class MultipleAttachmentsFieldSchema(_FieldSchemaBase, MultipleAttachmentsFieldConfig): pass  # noqa
class MultipleCollaboratorsFieldSchema(_FieldSchemaBase, MultipleCollaboratorsFieldConfig): pass  # noqa
class MultipleLookupValuesFieldSchema(_FieldSchemaBase, MultipleLookupValuesFieldConfig): pass  # noqa
class MultipleRecordLinksFieldSchema(_FieldSchemaBase, MultipleRecordLinksFieldConfig): pass  # noqa
class MultipleSelectsFieldSchema(_FieldSchemaBase, MultipleSelectsFieldConfig): pass  # noqa
class NumberFieldSchema(_FieldSchemaBase, NumberFieldConfig): pass  # noqa
class PercentFieldSchema(_FieldSchemaBase, PercentFieldConfig): pass  # noqa
class PhoneNumberFieldSchema(_FieldSchemaBase, PhoneNumberFieldConfig): pass  # noqa
class RatingFieldSchema(_FieldSchemaBase, RatingFieldConfig): pass  # noqa
class RichTextFieldSchema(_FieldSchemaBase, RichTextFieldConfig): pass  # noqa
class RollupFieldSchema(_FieldSchemaBase, RollupFieldConfig): pass  # noqa
class SingleCollaboratorFieldSchema(_FieldSchemaBase, SingleCollaboratorFieldConfig): pass  # noqa
class SingleLineTextFieldSchema(_FieldSchemaBase, SingleLineTextFieldConfig): pass  # noqa
class SingleSelectFieldSchema(_FieldSchemaBase, SingleSelectFieldConfig): pass  # noqa
class UrlFieldSchema(_FieldSchemaBase, UrlFieldConfig): pass  # noqa
class UnknownFieldSchema(_FieldSchemaBase, UnknownFieldConfig): pass  # noqa


FieldSchema: TypeAlias = Union[
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
# [[[end]]] (checksum: 3f8dd40da7b03b16f7299cd99365692c)
# fmt: on


update_forward_refs(vars())
