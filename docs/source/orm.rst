.. include:: substitutions.rst

ORM
==============

.. versionadded:: 1.0.0

.. warning:: This feature is experimental. Feel free to submit suggestions or feedback in our
    `Github repo <https://github.com/gtalarico/pyairtable>`_


Model
******

.. automodule:: pyairtable.orm.model

.. autoclass:: pyairtable.orm.model.Model
    :members:
    :undoc-members:

Fields
******

.. automodule:: pyairtable.orm.fields


Field Types
-----------
.. autoclass:: pyairtable.orm.fields.AutoNumberField
.. autoclass:: pyairtable.orm.fields.BarcodeField
.. autoclass:: pyairtable.orm.fields.ButtonField
.. autoclass:: pyairtable.orm.fields.CheckboxField
.. autoclass:: pyairtable.orm.fields.CollaboratorField
.. autoclass:: pyairtable.orm.fields.CountField
.. autoclass:: pyairtable.orm.fields.CreatedByField
.. autoclass:: pyairtable.orm.fields.CreatedTimeField
.. autoclass:: pyairtable.orm.fields.CurrencyField
.. autoclass:: pyairtable.orm.fields.DateField
.. autoclass:: pyairtable.orm.fields.DatetimeField
.. autoclass:: pyairtable.orm.fields.DurationField
.. autoclass:: pyairtable.orm.fields.EmailField
.. autoclass:: pyairtable.orm.fields.ExternalSyncSourceField
.. autoclass:: pyairtable.orm.fields.FloatField
.. autoclass:: pyairtable.orm.fields.IntegerField
.. autoclass:: pyairtable.orm.fields.LastModifiedByField
.. autoclass:: pyairtable.orm.fields.LastModifiedTimeField
.. autoclass:: pyairtable.orm.fields.LinkField
.. autoclass:: pyairtable.orm.fields.ListField
.. autoclass:: pyairtable.orm.fields.LookupField
.. autoclass:: pyairtable.orm.fields.MultipleAttachmentsField
.. autoclass:: pyairtable.orm.fields.MultipleCollaboratorsField
.. autoclass:: pyairtable.orm.fields.MultipleSelectField
.. autoclass:: pyairtable.orm.fields.NumberField
.. autoclass:: pyairtable.orm.fields.PercentField
.. autoclass:: pyairtable.orm.fields.PhoneNumberField
.. autoclass:: pyairtable.orm.fields.RatingField
.. autoclass:: pyairtable.orm.fields.RichTextField
.. autoclass:: pyairtable.orm.fields.SelectField
.. autoclass:: pyairtable.orm.fields.TextField
.. autoclass:: pyairtable.orm.fields.UrlField


Constants
---------
.. autodata:: pyairtable.orm.fields.ALL_FIELDS
.. autodata:: pyairtable.orm.fields.READONLY_FIELDS
.. autodata:: pyairtable.orm.fields.FIELD_TYPES_TO_CLASSES
