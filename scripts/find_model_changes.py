"""
Scans the API documentation on airtable.com and compares it to the models in pyAirtable.
Attempts to flag any places where the library is missing fields or has extra undocumented fields.
"""

import importlib
import json
import re
from functools import cached_property
from operator import attrgetter
from typing import Any, Dict, Iterator, List, Optional, Type

import click
import requests

from pyairtable.models._base import AirtableModel

API_PREFIX = "https://airtable.com/developers/web/api"
API_INTRO = f"{API_PREFIX}/introduction"
INITDATA_RE = r"<script[^>]*>\s*window\.initData = (\{.*\})\s*</script>"

SCAN_MODELS = {
    "pyairtable.api.enterprise:UserRemoved": "remove-user-from-enterprise.response",
    "pyairtable.api.enterprise:UserRemoved.Shared": "remove-user-from-enterprise.response/@shared",
    "pyairtable.api.enterprise:UserRemoved.Shared.Workspace": "remove-user-from-enterprise.response/@shared/@workspaces/items",
    "pyairtable.api.enterprise:UserRemoved.Unshared": "remove-user-from-enterprise.response/@unshared",
    "pyairtable.api.enterprise:UserRemoved.Unshared.Base": "remove-user-from-enterprise.response/@unshared/@bases/items",
    "pyairtable.api.enterprise:UserRemoved.Unshared.Interface": "remove-user-from-enterprise.response/@unshared/@interfaces/items",
    "pyairtable.api.enterprise:UserRemoved.Unshared.Workspace": "remove-user-from-enterprise.response/@unshared/@workspaces/items",
    "pyairtable.api.enterprise:DeleteUsersResponse": "delete-users-by-email.response",
    "pyairtable.api.enterprise:DeleteUsersResponse.UserInfo": "delete-users-by-email.response/@deletedUsers/items",
    "pyairtable.api.enterprise:DeleteUsersResponse.Error": "delete-users-by-email.response/@errors/items",
    "pyairtable.api.enterprise:ManageUsersResponse": "manage-user-membership.response",
    "pyairtable.api.enterprise:ManageUsersResponse.Error": "manage-user-membership.response/@errors/items",
    "pyairtable.api.enterprise:MoveError": "move-workspaces.response/@errors/items",
    "pyairtable.api.enterprise:MoveGroupsResponse": "move-user-groups.response",
    "pyairtable.api.enterprise:MoveWorkspacesResponse": "move-workspaces.response",
    "pyairtable.models.audit:AuditLogResponse": "audit-log-events.response",
    "pyairtable.models.audit:AuditLogEvent": "audit-log-events.response/@events/items",
    "pyairtable.models.audit:AuditLogEvent.Context": "audit-log-events.response/@events/items/@context",
    "pyairtable.models.audit:AuditLogEvent.Origin": "audit-log-events.response/@events/items/@origin",
    "pyairtable.models.audit:AuditLogActor": "schemas/audit-log-actor",
    "pyairtable.models.audit:AuditLogActor.UserInfo": "schemas/audit-log-actor/@user",
    "pyairtable.models.collaborator:Collaborator": "list-comments.response/@comments/items/@author",
    "pyairtable.models.comment:Comment": "list-comments.response/@comments/items",
    "pyairtable.models.comment:Reaction": "list-comments.response/@comments/items/@reactions/items",
    "pyairtable.models.comment:Reaction.EmojiInfo": "list-comments.response/@comments/items/@reactions/items/@emoji",
    "pyairtable.models.comment:Reaction.ReactingUser": "list-comments.response/@comments/items/@reactions/items/@reactingUser",
    "pyairtable.models.comment:Mentioned": "schemas/user-mentioned",
    "pyairtable.models.schema:BaseSchema": "get-base-schema.response",
    "pyairtable.models.schema:TableSchema": "schemas/table-model",
    "pyairtable.models.schema:Bases": "list-bases.response",
    "pyairtable.models.schema:Bases.Info": "list-bases.response/@bases/items",
    "pyairtable.models.schema:BaseCollaborators": "get-base-collaborators.response",
    "pyairtable.models.schema:BaseCollaborators.IndividualCollaborators": "get-base-collaborators.response/@individualCollaborators",
    "pyairtable.models.schema:BaseCollaborators.GroupCollaborators": "get-base-collaborators.response/@groupCollaborators",
    "pyairtable.models.schema:BaseCollaborators.InterfaceCollaborators": "get-base-collaborators.response/@interfaces/*",
    "pyairtable.models.schema:BaseCollaborators.InviteLinks": "get-base-collaborators.response/@inviteLinks",
    "pyairtable.models.schema:BaseCollaborators.SensitivityLabel": "get-base-collaborators.response/@sensitivityLabel",
    "pyairtable.models.schema:BaseShares": "list-shares.response",
    "pyairtable.models.schema:BaseShares.Info": "list-shares.response/@shares/items",
    "pyairtable.models.schema:ViewSchema": "get-view-metadata.response",
    "pyairtable.models.schema:InviteLink": "schemas/invite-link",
    "pyairtable.models.schema:WorkspaceInviteLink": "schemas/invite-link",
    "pyairtable.models.schema:InterfaceInviteLink": "schemas/invite-link",
    "pyairtable.models.schema:EnterpriseInfo": "get-enterprise.response",
    "pyairtable.models.schema:EnterpriseInfo.EmailDomain": "get-enterprise.response/@emailDomains/items",
    "pyairtable.models.schema:EnterpriseInfo.AggregatedIds": "get-enterprise.response/@aggregated",
    "pyairtable.models.schema:WorkspaceCollaborators": "get-workspace-collaborators.response",
    "pyairtable.models.schema:WorkspaceCollaborators.Restrictions": "get-workspace-collaborators.response/@workspaceRestrictions",
    "pyairtable.models.schema:WorkspaceCollaborators.GroupCollaborators": "get-workspace-collaborators.response/@groupCollaborators",
    "pyairtable.models.schema:WorkspaceCollaborators.IndividualCollaborators": "get-workspace-collaborators.response/@individualCollaborators",
    "pyairtable.models.schema:WorkspaceCollaborators.InviteLinks": "get-workspace-collaborators.response/@inviteLinks",
    "pyairtable.models.schema:GroupCollaborator": "schemas/group-collaborator",
    "pyairtable.models.schema:IndividualCollaborator": "schemas/individual-collaborator",
    "pyairtable.models.schema:BaseGroupCollaborator": "schemas/base-group-collaborator",
    "pyairtable.models.schema:BaseIndividualCollaborator": "schemas/base-individual-collaborator",
    "pyairtable.models.schema:BaseInviteLink": "schemas/base-invite-link",
    "pyairtable.models.schema:Collaborations": "schemas/collaborations",
    "pyairtable.models.schema:Collaborations.BaseCollaboration": "schemas/collaborations/@baseCollaborations/items",
    "pyairtable.models.schema:Collaborations.InterfaceCollaboration": "schemas/collaborations/@interfaceCollaborations/items",
    "pyairtable.models.schema:Collaborations.WorkspaceCollaboration": "schemas/collaborations/@workspaceCollaborations/items",
    "pyairtable.models.schema:UserInfo": "get-user-by-id.response",
    "pyairtable.models.schema:UserInfo.AggregatedIds": "get-user-by-id.response/@aggregated",
    "pyairtable.models.schema:UserInfo.DescendantIds": "get-user-by-id.response/@descendants/*",
    "pyairtable.models.schema:UserGroup": "get-user-group.response",
    "pyairtable.models.schema:UserGroup.Member": "get-user-group.response/@members/items",
    "pyairtable.models.webhook:Webhook": "list-webhooks.response/@webhooks/items",
    "pyairtable.models.webhook:WebhookNotificationResult": "schemas/webhooks-notification",
    "pyairtable.models.webhook:WebhookError": "schemas/webhooks-notification/@error",
    "pyairtable.models.webhook:WebhookPayloads": "list-webhook-payloads.response",
    "pyairtable.models.webhook:WebhookPayload": "schemas/webhooks-payload",
    "pyairtable.models.webhook:WebhookPayload.ActionMetadata": "schemas/webhooks-action",
    "pyairtable.models.webhook:WebhookPayload.FieldChanged": "schemas/webhooks-table-changed/@changedFieldsById/*",
    "pyairtable.models.webhook:WebhookPayload.FieldInfo": "schemas/webhooks-table-changed/@changedFieldsById/*/@current",
    "pyairtable.models.webhook:WebhookPayload.RecordChanged": "schemas/webhooks-changed-record/*",
    "pyairtable.models.webhook:WebhookPayload.RecordCreated": "schemas/webhooks-created-record/*",
    "pyairtable.models.webhook:WebhookPayload.TableChanged": "schemas/webhooks-table-changed",
    "pyairtable.models.webhook:WebhookPayload.TableChanged.ChangedMetadata": "schemas/webhooks-table-changed/@changedMetadata",
    "pyairtable.models.webhook:WebhookPayload.TableInfo": "schemas/webhooks-table-changed/@changedMetadata/@current",
    "pyairtable.models.webhook:WebhookPayload.TableCreated": "schemas/webhooks-table-created",
    "pyairtable.models.webhook:WebhookPayload.ViewChanged": "schemas/webhooks-table-changed/@changedViewsById/*",
    "pyairtable.models.webhook:CreateWebhook": "create-a-webhook.request",
    "pyairtable.models.webhook:CreateWebhookResponse": "create-a-webhook.response",
    "pyairtable.models.webhook:WebhookSpecification": "create-a-webhook.request/@specification",
    "pyairtable.models.webhook:WebhookSpecification.Options": "schemas/webhooks-specification",
    "pyairtable.models.webhook:WebhookSpecification.Includes": "schemas/webhooks-specification/@includes",
    "pyairtable.models.webhook:WebhookSpecification.Filters": "schemas/webhooks-specification/@filters",
    "pyairtable.models.webhook:WebhookSpecification.SourceOptions": "schemas/webhooks-specification/@filters/@sourceOptions",
    "pyairtable.models.webhook:WebhookSpecification.SourceOptions.FormSubmission": "schemas/webhooks-specification/@filters/@sourceOptions/@formSubmission",
    "pyairtable.models.webhook:WebhookSpecification.SourceOptions.FormPageSubmission": "schemas/webhooks-specification/@filters/@sourceOptions/@formPageSubmission",
    "pyairtable.models.schema:TableSchema.DateDependency": "schemas/date-dependency-settings",
}

IGNORED = [
    "pyairtable.models.audit.AuditLogResponse.Pagination",  # pagination, not exposed
    "pyairtable.models.schema.NestedId",  # internal
    "pyairtable.models.schema.NestedFieldId",  # internal
    "pyairtable.models.schema.Bases.offset",  # pagination, not exposed
    "pyairtable.models.schema.BaseCollaborators.collaborators",  # deprecated
    "pyairtable.models.schema.WorkspaceCollaborators.collaborators",  # deprecated
    "pyairtable.models.webhook.WebhookPayload.cursor",  # pyAirtable provides this
    "pyairtable.models.schema.BaseShares.Info.shareTokenPrefix",  # deprecated
    "pyairtable.models.webhook.WebhookPayload.CellValuesByFieldId",  # undefined in schema
    "pyairtable.models.webhook.WebhookNotification",  # undefined in schema
]


@click.command()
@click.option(
    "--save",
    "save_apidata",
    help="Save API schema information to a file.",
    type=click.Path(writable=True),
)
def main(save_apidata: Optional[str]) -> None:
    api_data = get_api_data()
    if save_apidata:
        with open(save_apidata, "w") as f:
            json.dump(api_data, f, indent=2, sort_keys=True)

    identify_missing_fields(api_data)
    identify_unscanned_classes(api_data)


def identify_missing_fields(api_data: "ApiData") -> None:
    issues: List[str] = []

    # Find missing/extra fields
    for model_path, data_path in SCAN_MODELS.items():
        modname, clsname = model_path.split(":", 1)
        model_module = importlib.import_module(modname)
        model_cls = attrgetter(clsname)(model_module)
        # Use obj/@thing as shorthand for obj/properties/thing
        data_path = data_path.replace("/@", "/properties/")
        # Use obj/* as shorthand for obj/additionalProperties
        data_path = re.sub(r"/\*(/|$)", r"/additionalProperties\1", data_path)
        # Use list-bases.request as shorthand for operations/list-bases/request/schema
        # and list-bases.response as shorthand for operations/list-bases/response/schema
        data_path = re.sub(
            r"(^|/)([a-zA-Z_-]+)\.(request|response)(/|$)",
            r"\1operations/\2/\3/schema\4",
            data_path,
        )
        issues.extend(scan_schema(model_cls, api_data.get_nested(data_path)))

    if not issues:
        print("No missing/extra fields found in scanned classes")
    else:
        for issue in issues:
            print(issue)


def identify_unscanned_classes(api_data: "ApiData") -> None:
    issues: List[str] = []

    # Find unscanned model classes
    modules = sorted({model_path.split(":")[0] for model_path in SCAN_MODELS})
    for modname in modules:
        if not ignore_name(modname):
            mod = importlib.import_module(modname)
            issues.extend(scan_missing(mod, prefix=(modname + ":")))

    if not issues:
        print("No unscanned classes found in scanned modules")
    else:
        for issue in issues:
            print(issue)


def ignore_name(name: str) -> bool:
    if "." in name and any(ignore_name(n) for n in name.split(".")):
        return True
    return (
        name in IGNORED
        or name.startswith("_")
        or name.endswith("FieldConfig")
        or name.endswith("FieldOptions")
        or name.endswith("FieldSchema")
    )


class ApiData(Dict[str, Any]):
    """
    Wrapper around ``dict`` that adds convenient behavior for reading the API definition.
    """

    def __getitem__(self, key: str) -> Any:
        # handy shortcuts
        if key == "operations":
            return self.by_operation
        if key == "schemas":
            return self.by_model_name
        return super().__getitem__(key)

    def get_nested(self, path: str, separator: str = "/") -> Any:
        """
        Retrieves nested objects with a path-like syntax.
        """
        get_from = self
        traversed = []
        try:
            while separator in path:
                next_key, path = path.split(separator, 1)
                traversed.append(next_key)
                get_from = get_from[next_key]
            traversed.append(path)
            return get_from[path]
        except KeyError as exc:
            exc.args = tuple(traversed)
            raise exc

    @cached_property
    def by_operation(self) -> Dict[str, Dict[str, Any]]:
        """
        Simplifies traversal of request/response information for defined web API operations,
        grouping them by the operation name instead of path/method.
        """
        result: Dict[str, Dict[str, Any]] = {}
        paths: Dict[str, Dict[str, Any]] = self["openApi"]["paths"]
        methodinfo_dicts = [
            methodinfo
            for pathinfo in paths.values()
            for methodinfo in pathinfo.values()
            if isinstance(methodinfo, dict)
        ]
        for methodinfo in methodinfo_dicts:
            methodname = str(methodinfo["operationId"]).lower()
            r = result[methodname] = {}
            try:
                r["response"] = methodinfo["responses"]["200"]["content"]["application/json"]  # fmt: skip
            except KeyError:
                pass
            try:
                r["request"] = methodinfo["requestBody"]["content"]["application/json"]  # fmt: skip
            except KeyError:
                pass

        return result

    @cached_property
    def by_model_name(self) -> Dict[str, Dict[str, Any]]:
        """
        Simplifies traversal of schema information by preemptively collapsing
        anyOf models
        """
        return {
            key: self.collapse_schema(self.get_model(name))
            for name in self["openApi"]["components"]["schemas"]
            for key in (str(name), str(name).lower())
        }

    def get_model(self, name: str) -> Dict[str, Any]:
        """
        Retrieve a model schema by name.
        """
        return self.collapse_schema(
            self.get_nested(f"openApi/components/schemas/{name}")
        )

    def collapse_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge together properties of all entries in anyOf or allOf schemas.
        This is acceptable for our use case, but a bad idea in most other cases.
        """
        if set(schema) == {"$ref"}:
            if (ref := schema["$ref"]).startswith("#/components/schemas/"):
                return self.collapse_schema(self.get_model(ref.split("/")[-1]))
            raise ValueError(f"unhandled $ref: {ref}")

        for key in ("anyOf", "allOf"):
            if key not in schema:
                continue
            collected_properties = {}
            subschema: Dict[str, Any]
            for subschema in list(schema[key]):
                if subschema.get("type") == "object" or "$ref" in subschema:
                    collected_properties.update(
                        self.collapse_schema(subschema).get("properties", {})
                    )
            return {"properties": collected_properties}

        return schema


def get_api_data() -> ApiData:
    """
    Retrieve API information.
    """
    response = requests.get(API_INTRO)
    response.raise_for_status()
    match = re.search(INITDATA_RE, response.text)
    if not match:
        raise RuntimeError(f"could not find {INITDATA_RE!r} in {API_INTRO}")
    return ApiData(json.loads(match.group(1)))


def scan_schema(cls: Type[AirtableModel], schema: Dict[str, Any]) -> Iterator[str]:
    """
    Yield error messages for missing or undocumented fields.
    """

    name = f"{cls.__module__}.{cls.__qualname__}"
    model_aliases = {f.alias for f in cls.model_fields.values() if f.alias}
    api_properties = set(schema["properties"])
    missing_keys = api_properties - model_aliases
    extra_keys = model_aliases - api_properties
    for missing_key in missing_keys:
        if not ignore_name(f"{name}.{missing_key}"):
            yield f"{name} is missing field: {missing_key}"
    for extra_key in extra_keys:
        if not ignore_name(f"{name}.{extra_key}"):
            yield (f"{name} has undocumented field: {extra_key}")


def scan_missing(container: Any, prefix: str) -> Iterator[str]:
    """
    Yield error messages for models within the given container which were not scanned.
    """
    for name, obj in vars(container).items():
        if not isinstance(obj, type) or not issubclass(obj, AirtableModel):
            continue
        # ignore imported models in other modules
        if not prefix.startswith(obj.__module__):
            continue
        if ignore_name(f"{obj.__module__}.{obj.__qualname__}"):
            continue
        if (subpath := f"{prefix}{name}") not in SCAN_MODELS:
            yield f"{subpath} was not scanned"
        yield from scan_missing(obj, prefix=(subpath + "."))


if __name__ == "__main__":
    main()
