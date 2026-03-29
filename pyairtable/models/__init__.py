# Putting a selection of model classes into pyairtable.models
# is how we indicate the "public API" vs. implementation details.
# If it's not in here, we don't expect implementers to call it directly.

"""
pyAirtable will wrap certain API responses in type-annotated models,
some of which will be deeply nested within each other. Models which
implementers can interact with directly are documented below.
Nested or internal models are documented in each submodule.

Due to its complexity, the :mod:`pyairtable.models.schema` module is
documented separately, and none of its classes are exposed here.
"""

from pyairtable.models.audit import AuditLogEvent, AuditLogResponse
from pyairtable.models.collaborator import Collaborator
from pyairtable.models.comment import Comment
from pyairtable.models.webhook import Webhook, WebhookNotification, WebhookPayload

__all__ = [
    "AuditLogResponse",
    "AuditLogEvent",
    "Collaborator",
    "Comment",
    "Webhook",
    "WebhookNotification",
    "WebhookPayload",
]
