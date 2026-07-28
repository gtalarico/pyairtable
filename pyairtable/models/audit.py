from datetime import datetime
from typing import Any, TypeAlias

import pydantic

from pyairtable.models._base import AirtableModel, rebuild_models


class AuditLogResponse(AirtableModel):
    """
    Represents a page of audit log events.

    See `Audit log events <https://airtable.com/developers/web/api/audit-log-events>`__
    for more information on how to interpret this data structure.
    """

    events: list["AuditLogEvent"]
    pagination: "AuditLogResponse.Pagination | None" = None

    class Pagination(AirtableModel):
        next: str | None = None
        previous: str | None = None


class AuditLogEvent(AirtableModel):
    """
    Represents a single audit log event.

    See `Audit log events <https://airtable.com/developers/web/api/audit-log-events>`__
    for more information on how to interpret this data structure.

    To avoid namespace conflicts with the Pydantic library, the
    ``modelId`` and ``modelType`` fields from the Airtable API are
    represented as fields named ``object_id`` and ``object_type``.
    """

    id: str
    timestamp: datetime
    action: str
    actor: "AuditLogActor"
    object_id: str = pydantic.Field(alias="modelId")
    object_type: str = pydantic.Field(alias="modelType")
    payload: "AuditLogPayload"
    payload_version: str
    context: "AuditLogEvent.Context"
    origin: "AuditLogEvent.Origin"

    class Context(AirtableModel):
        base_id: str | None = None
        action_id: str
        enterprise_account_id: str
        descendant_enterprise_account_id: str | None = None
        interface_id: str | None = None
        workspace_id: str | None = None

    class Origin(AirtableModel):
        ip_address: str
        user_agent: str
        oauth_access_token_id: str | None = None
        personal_access_token_id: str | None = None
        session_id: str | None = None


class AuditLogActor(AirtableModel):
    type: str
    user: "AuditLogActor.UserInfo | None" = None
    view_id: str | None = None
    automation_id: str | None = None

    class UserInfo(AirtableModel):
        id: str
        email: str
        name: str | None = None


# Placeholder until we can parse https://airtable.com/developers/web/api/audit-log-event-types
AuditLogPayload: TypeAlias = dict[str, Any]


rebuild_models(vars())
