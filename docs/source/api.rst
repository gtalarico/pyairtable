.. include:: _warn_latest.rst
.. include:: _substitutions.rst


API Reference
=============


API: pyairtable
*******************************

.. autoclass:: pyairtable.Api
    :members:

.. autoclass:: pyairtable.Base
    :members:

.. autoclass:: pyairtable.Table
    :members:

.. autoclass:: pyairtable.Workspace
    :members:

.. autoclass:: pyairtable.Enterprise
    :members:

.. autofunction:: pyairtable.retry_strategy


API: pyairtable.api.enterprise
*******************************

.. automodule:: pyairtable.api.enterprise
    :members:
    :exclude-members: Enterprise


API: pyairtable.api.types
*******************************

.. automodule:: pyairtable.api.types
    :members:


API: pyairtable.exceptions
*******************************

.. automodule:: pyairtable.exceptions
    :members:


API: pyairtable.formulas
*******************************

.. automodule:: pyairtable.formulas
    :members:


API: pyairtable.models
*******************************

.. automodule:: pyairtable.models
    :members:
    :inherited-members: AirtableModel


API: pyairtable.models.comment
-------------------------------

.. automodule:: pyairtable.models.comment
    :members:
    :exclude-members: Comment
    :inherited-members: AirtableModel


API: pyairtable.models.schema
-------------------------------

.. automodule:: pyairtable.models.schema
    :members:
    :inherited-members: AirtableModel

.. automethod:: pyairtable.models.schema.parse_field_schema


API: pyairtable.models.webhook
-------------------------------

.. automodule:: pyairtable.models.webhook
    :members:
    :exclude-members: Webhook, WebhookNotification, WebhookPayload
    :inherited-members: AirtableModel


API: pyairtable.orm
*******************************

.. autoclass:: pyairtable.orm.Model
    :members:


API: pyairtable.orm.fields
*******************************

.. automodule:: pyairtable.orm.fields
    :members:
    :exclude-members: valid_types, contains_type
    :no-inherited-members:


API: pyairtable.testing
*******************************

.. automodule:: pyairtable.testing
    :members:


API: pyairtable.utils
*******************************

.. automodule:: pyairtable.utils
    :members:
