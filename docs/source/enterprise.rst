.. include:: _substitutions.rst
.. include:: _warn_latest.rst

Enterprise Features
==============================


pyAirtable exposes a number of classes and methods for interacting with enterprise organizations.
The following methods are only available on an `Enterprise plan <https://airtable.com/pricing>`__.
If you call one of them against a base that is not part of an enterprise workspace, Airtable will
return a 404 error, and pyAirtable will add a reminder to the exception to check your billing plan.

.. automethod:: pyairtable.Api.enterprise
    :noindex:

.. automethod:: pyairtable.Base.collaborators
    :noindex:

.. automethod:: pyairtable.Base.shares
    :noindex:

.. automethod:: pyairtable.Workspace.collaborators
    :noindex:

.. automethod:: pyairtable.Enterprise.info
    :noindex:

.. automethod:: pyairtable.Enterprise.audit_log
    :noindex:
