"""
Scans the API documentation on airtable.com and compares it to the models in pyAirtable.
Attempts to flag any places where the library is missing fields or has extra undocumented fields.
"""

import importlib
import json
import re
from functools import cached_property
from operator import attrgetter
from typing import Any, Dict, Iterator, List, Type

import requests

from pyairtable.models._base import AirtableModel

API_PREFIX = "https://airtable.com/developers/web/api"
API_INTRO = f"{API_PREFIX}/introduction"
INITDATA_RE = r"<script[^>]*>\s*window\.initData = (\{.*\})\s*</script>"

SCAN_MODELS = {
    "pyairtable.api.enterprise:UserRemoved": "operations:remove-user-from-enterprise:response:schema",
    "pyairtable.api.enterprise:UserRemoved.Shared": "operations:remove-user-from-enterprise:response:schema:@shared",
    "pyairtable.api.enterprise:UserRemoved.Shared.Workspace": "operations:remove-user-from-enterprise:response:schema:@shared:@workspaces:items",
    "pyairtable.api.enterprise:UserRemoved.Unshared": "operations:remove-user-from-enterprise:response:schema:@unshared",
    "pyairtable.api.enterprise:UserRemoved.Unshared.Base": "operations:remove-user-from-enterprise:response:schema:@unshared:@bases:items",
    "pyairtable.api.enterprise:UserRemoved.Unshared.Interface": "operations:remove-user-from-enterprise:response:schema:@unshared:@interfaces:items",
    "pyairtable.api.enterprise:UserRemoved.Unshared.Workspace": "operations:remove-user-from-enterprise:response:schema:@unshared:@workspaces:items",
    "pyairtable.api.enterprise:DeleteUsersResponse": "operations:delete-users-by-email:response:schema",
    "pyairtable.api.enterprise:DeleteUsersResponse.UserInfo": "operations:delete-users-by-email:response:schema:@deletedUsers:items",
    "pyairtable.api.enterprise:DeleteUsersResponse.Error": "operations:delete-users-by-email:response:schema:@errors:items",
    "pyairtable.api.enterprise:ManageUsersResponse": "operations:manage-user-membership:response:schema",
    "pyairtable.api.enterprise:ManageUsersResponse.Error": "operations:manage-user-membership:response:schema:@errors:items",
    "pyairtable.api.enterprise:MoveError": "operations:move-workspaces:response:schema:@errors:items",
    "pyairtable.api.enterprise:MoveGroupsResponse": "operations:move-user-groups:response:schema",
    "pyairtable.api.enterprise:MoveWorkspacesResponse": "operations:move-workspaces:response:schema",
    "pyairtable.models.audit:AuditLogResponse": "operations:audit-log-events:response:schema",
    "pyairtable.models.audit:AuditLogEvent": "operations:audit-log-events:response:schema:@events:items",
    "pyairtable.models.audit:AuditLogEvent.Context": "operations:audit-log-events:response:schema:@events:items:@context",
    "pyairtable.models.audit:AuditLogEvent.Origin": "operations:audit-log-events:response:schema:@events:items:@origin",
    "pyairtable.models.audit:AuditLogActor": "schemas:audit-log-actor",
    "pyairtable.models.audit:AuditLogActor.UserInfo": "schemas:audit-log-actor:@user",
    "pyairtable.models.collaborator:Collaborator": "operations:list-comments:response:schema:@comments:items:@author",
    "pyairtable.models.comment:Comment": "operations:list-comments:response:schema:@comments:items",
    "pyairtable.models.comment:Reaction": "operations:list-comments:response:schema:@comments:items:@reactions:items",
    "pyairtable.models.comment:Reaction.EmojiInfo": "operations:list-comments:response:schema:@comments:items:@reactions:items:@emoji",
    "pyairtable.models.comment:Reaction.ReactingUser": "operations:list-comments:response:schema:@comments:items:@reactions:items:@reactingUser",
    "pyairtable.models.comment:Mentioned": "schemas:user-mentioned",
    "pyairtable.models.schema:BaseSchema": "operations:get-base-schema:response:schema",
    "pyairtable.models.schema:TableSchema": "schemas:table-model",
    "pyairtable.models.schema:Bases": "operations:list-bases:response:schema",
    "pyairtable.models.schema:Bases.Info": "operations:list-bases:response:schema:@bases:items",
    "pyairtable.models.schema:BaseCollaborators": "operations:get-base-collaborators:response:schema",
    "pyairtable.models.schema:BaseCollaborators.IndividualCollaborators": "operations:get-base-collaborators:response:schema:@individualCollaborators",
    "pyairtable.models.schema:BaseCollaborators.GroupCollaborators": "operations:get-base-collaborators:response:schema:@groupCollaborators",
    "pyairtable.models.schema:BaseCollaborators.InterfaceCollaborators": "operations:get-base-collaborators:response:schema:@interfaces:*",
    "pyairtable.models.schema:BaseCollaborators.InviteLinks": "operations:get-base-collaborators:response:schema:@inviteLinks",
    "pyairtable.models.schema:BaseShares": "operations:list-shares:response:schema",
    "pyairtable.models.schema:BaseShares.Info": "operations:list-shares:response:schema:@shares:items",
    "pyairtable.models.schema:ViewSchema": "operations:get-view-metadata:response:schema",
    "pyairtable.models.schema:InviteLink": "schemas:invite-link",
    "pyairtable.models.schema:WorkspaceInviteLink": "schemas:invite-link",
    "pyairtable.models.schema:InterfaceInviteLink": "schemas:invite-link",
    "pyairtable.models.schema:EnterpriseInfo": "operations:get-enterprise:response:schema",
    "pyairtable.models.schema:EnterpriseInfo.EmailDomain": "operations:get-enterprise:response:schema:@emailDomains:items",
    "pyairtable.models.schema:EnterpriseInfo.AggregatedIds": "operations:get-enterprise:response:schema:@aggregated",
    "pyairtable.models.schema:WorkspaceCollaborators": "operations:get-workspace-collaborators:response:schema",
    "pyairtable.models.schema:WorkspaceCollaborators.Restrictions": "operations:get-workspace-collaborators:response:schema:@workspaceRestrictions",
    "pyairtable.models.schema:WorkspaceCollaborators.GroupCollaborators": "operations:get-workspace-collaborators:response:schema:@groupCollaborators",
    "pyairtable.models.schema:WorkspaceCollaborators.IndividualCollaborators": "operations:get-workspace-collaborators:response:schema:@individualCollaborators",
    "pyairtable.models.schema:WorkspaceCollaborators.InviteLinks": "operations:get-workspace-collaborators:response:schema:@inviteLinks",
    "pyairtable.models.schema:GroupCollaborator": "schemas:group-collaborator",
    "pyairtable.models.schema:IndividualCollaborator": "schemas:individual-collaborator",
    "pyairtable.models.schema:BaseGroupCollaborator": "schemas:base-group-collaborator",
    "pyairtable.models.schema:BaseIndividualCollaborator": "schemas:base-individual-collaborator",
    "pyairtable.models.schema:BaseInviteLink": "schemas:base-invite-link",
    "pyairtable.models.schema:Collaborations": "schemas:collaborations",
    "pyairtable.models.schema:Collaborations.BaseCollaboration": "schemas:collaborations:@baseCollaborations:items",
    "pyairtable.models.schema:Collaborations.InterfaceCollaboration": "schemas:collaborations:@interfaceCollaborations:items",
    "pyairtable.models.schema:Collaborations.WorkspaceCollaboration": "schemas:collaborations:@workspaceCollaborations:items",
    "pyairtable.models.schema:UserInfo": "operations:get-user-by-id:response:schema",
    "pyairtable.models.schema:UserInfo.AggregatedIds": "operations:get-user-by-id:response:schema:@aggregated",
    "pyairtable.models.schema:UserInfo.DescendantIds": "operations:get-user-by-id:response:schema:@descendants:*",
    "pyairtable.models.schema:UserGroup": "operations:get-user-group:response:schema",
    "pyairtable.models.schema:UserGroup.Member": "operations:get-user-group:response:schema:@members:items",
    "pyairtable.models.webhook:Webhook": "operations:list-webhooks:response:schema:@webhooks:items",
    "pyairtable.models.webhook:WebhookNotificationResult": "schemas:webhooks-notification",
    "pyairtable.models.webhook:WebhookError": "schemas:webhooks-notification:@error",
    "pyairtable.models.webhook:WebhookPayloads": "operations:list-webhook-payloads:response:schema",
    "pyairtable.models.webhook:WebhookPayload": "schemas:webhooks-payload",
    "pyairtable.models.webhook:WebhookPayload.ActionMetadata": "schemas:webhooks-action",
    "pyairtable.models.webhook:WebhookPayload.FieldChanged": "schemas:webhooks-table-changed:@changedFieldsById:*",
    "pyairtable.models.webhook:WebhookPayload.FieldInfo": "schemas:webhooks-table-changed:@changedFieldsById:*:@current",
    "pyairtable.models.webhook:WebhookPayload.RecordChanged": "schemas:webhooks-changed-record:*",
    "pyairtable.models.webhook:WebhookPayload.RecordCreated": "schemas:webhooks-created-record:*",
    "pyairtable.models.webhook:WebhookPayload.TableChanged": "schemas:webhooks-table-changed",
    "pyairtable.models.webhook:WebhookPayload.TableChanged.ChangedMetadata": "schemas:webhooks-table-changed:@changedMetadata",
    "pyairtable.models.webhook:WebhookPayload.TableInfo": "schemas:webhooks-table-changed:@changedMetadata:@current",
    "pyairtable.models.webhook:WebhookPayload.TableCreated": "schemas:webhooks-table-created",
    "pyairtable.models.webhook:WebhookPayload.ViewChanged": "schemas:webhooks-table-changed:@changedViewsById:*",
    "pyairtable.models.webhook:CreateWebhook": "operations:create-a-webhook:request:schema",
    "pyairtable.models.webhook:CreateWebhookResponse": "operations:create-a-webhook:response:schema",
    "pyairtable.models.webhook:WebhookSpecification": "operations:create-a-webhook:request:schema:@specification",
    "pyairtable.models.webhook:WebhookSpecification.Options": "schemas:webhooks-specification",
    "pyairtable.models.webhook:WebhookSpecification.Includes": "schemas:webhooks-specification:@includes",
    "pyairtable.models.webhook:WebhookSpecification.Filters": "schemas:webhooks-specification:@filters",
    "pyairtable.models.webhook:WebhookSpecification.SourceOptions": "schemas:webhooks-specification:@filters:@sourceOptions",
    "pyairtable.models.webhook:WebhookSpecification.SourceOptions.FormSubmission": "schemas:webhooks-specification:@filters:@sourceOptions:@formSubmission",
    "pyairtable.models.webhook:WebhookSpecification.SourceOptions.FormPageSubmission": "schemas:webhooks-specification:@filters:@sourceOptions:@formPageSubmission",
    "pyairtable.models.schema:TableSchema.DateDependency": "schemas:date-dependency-settings",
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


def main() -> None:
    initdata = get_api_data()
    identify_missing_fields(initdata)
    identify_unscanned_classes(initdata)


def identify_missing_fields(initdata: "ApiData") -> None:
    issues: List[str] = []

    # Find missing/extra fields
    for model_path, initdata_path in SCAN_MODELS.items():
        modname, clsname = model_path.split(":", 1)
        model_module = importlib.import_module(modname)
        model_cls = attrgetter(clsname)(model_module)
        initdata_path = initdata_path.replace(":@", ":properties:")
        initdata_path = re.sub(r":\*(:|$)", r":additionalProperties\1", initdata_path)
        issues.extend(scan_schema(model_cls, initdata.get_nested(initdata_path)))

    if not issues:
        print("No missing/extra fields found in scanned classes")
    else:
        for issue in issues:
            print(issue)


def identify_unscanned_classes(initdata: "ApiData") -> None:
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

    def get_nested(self, path: str, separator: str = ":") -> Any:
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
            self.get_nested(f"openApi:components:schemas:{name}")
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
