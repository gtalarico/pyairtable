.. include:: substitutions.rst

ORM
==============

.. warning:: This feature is experimental. Feel free to submit suggestions or feedback in our
    `Github repo <https://github.com/gtalarico/pyairtable>`_


Defining Models
---------------

The :class:`~pyairtable.orm.Model` class allows you create ORM-style classes for your Airtable tables.

.. code-block: python::

    from pyairtable.orm import Model, fields as F
    class Contact(Model):
        first_name = F.TextField("First Name")
        last_name = F.TextField("Last Name")
        email = F.EmailField("Email")
        is_registered = F.CheckboxField("Registered")
        company = F.LinkField("Company", Company, lazy=False)

        class Meta:
            base_id = "appaPqizdsNHDvlEm"
            table_name = "Contact"
            api_key = "keyapikey"


Once you have a class, you can create new objects to represent your
Airtable records. Call :meth:`~pyairtable.orm.Model.save` to save the
newly created object to the Airtable API.

    >>> contact = Contact(
    ...     first_name="Mike",
    ...     last_name="McDonalds",
    ...     email="mike@mcd.com",
    ...     is_registered=False
    ... )
    >>> assert contact.id is None
    >>> contact.exists()
    False
    >>> assert contact.save()
    >>> contact.exists()
    True
    >>> contact.id
    'recS6qSLw0OCA6Xul'


You can read and modify attributes, then call :meth:`~pyairtable.orm.Model.save`
when you're ready to save your changes to the API.

    >>> contact = Contact.from_id("recS6qSLw0OCA6Xul")
    >>> assert contact.is_registered is False
    >>> contact.is_registered = True
    >>> contact.save()

To refresh a record from the API, use :meth:`~pyairtable.orm.Model.fetch`:

    >>> contact.is_registered = False
    >>> contact.fetch()
    >>> contact.is_registered
    True

Finally, you can use :meth:`~pyairtable.orm.Model.delete` to delete the record:

    >>> contact.delete()
    True

There are also :meth:`~pyairtable.orm.Model.batch_save` and
:meth:`~pyairtable.orm.Model.batch_delete` for when you need to
create, modify, or delete several records at once:

    >>> contacts = Contact.all()
    >>> contacts.append(Contact(first_name="Alice", email="alice@example.com"))
    >>> Contact.batch_save(contacts)
    >>> Contact.batch_delete(contacts)


Supported Fields
----------------

The following grid maps each of the supported field types in pyAirtable
to the Airtable field type. Any field with a lock icon is read-only by default.
For more information on how the Airtable API represents each of its field types,
read `Field types and cell values <https://airtable.com/developers/web/api/field-model>`__.

..  [[[cog
    import re
    from operator import attrgetter
    from pyairtable.orm import fields

    cog.outl("..")
    cog.outl(".. list-table::")
    cog.outl("   :header-rows: 1\n")
    cog.outl("   * - ORM field class")
    cog.outl("     - Airtable field type(s)")

    for cls in sorted(fields.ALL_FIELDS, key=attrgetter("__name__")):
        links = re.findall(r"`.+? <.*?field-model.*?>`", cls.__doc__ or "")
        ro = ' 🔒' if cls.readonly else ''
        cog.outl(f"   * - :class:`~pyairtable.orm.fields.{cls.__name__}`{ro}")
        cog.outl(f"     - {', '.join(f'{link}__' for link in links) if links else '(see docs)'}")
    ]]]
..
.. list-table::
   :header-rows: 1

   * - ORM field class
     - Airtable field type(s)
   * - :class:`~pyairtable.orm.fields.AutoNumberField` 🔒
     - `Auto number <https://airtable.com/developers/web/api/field-model#autonumber>`__
   * - :class:`~pyairtable.orm.fields.BarcodeField`
     - `Barcode <https://airtable.com/developers/web/api/field-model#barcode>`__
   * - :class:`~pyairtable.orm.fields.ButtonField` 🔒
     - `Button <https://airtable.com/developers/web/api/field-model#button>`__
   * - :class:`~pyairtable.orm.fields.CheckboxField`
     - `Checkbox <https://airtable.com/developers/web/api/field-model#checkbox>`__
   * - :class:`~pyairtable.orm.fields.CollaboratorField`
     - `Collaborator <https://airtable.com/developers/web/api/field-model#collaborator>`__
   * - :class:`~pyairtable.orm.fields.CountField` 🔒
     - `Count <https://airtable.com/developers/web/api/field-model#count>`__
   * - :class:`~pyairtable.orm.fields.CreatedByField` 🔒
     - `Created by <https://airtable.com/developers/web/api/field-model#createdby>`__
   * - :class:`~pyairtable.orm.fields.CreatedTimeField` 🔒
     - `Created time <https://airtable.com/developers/web/api/field-model#createdtime>`__
   * - :class:`~pyairtable.orm.fields.CurrencyField`
     - `Currency <https://airtable.com/developers/web/api/field-model#currencynumber>`__
   * - :class:`~pyairtable.orm.fields.DateField`
     - `Date <https://airtable.com/developers/web/api/field-model#dateonly>`__
   * - :class:`~pyairtable.orm.fields.DatetimeField`
     - `Date and time <https://airtable.com/developers/web/api/field-model#dateandtime>`__
   * - :class:`~pyairtable.orm.fields.DurationField`
     - `Duration <https://airtable.com/developers/web/api/field-model#durationnumber>`__
   * - :class:`~pyairtable.orm.fields.EmailField`
     - `Email <https://airtable.com/developers/web/api/field-model#email>`__
   * - :class:`~pyairtable.orm.fields.ExternalSyncSourceField` 🔒
     - `Sync source <https://airtable.com/developers/web/api/field-model#syncsource>`__
   * - :class:`~pyairtable.orm.fields.FloatField`
     - `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__
   * - :class:`~pyairtable.orm.fields.IntegerField`
     - `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__
   * - :class:`~pyairtable.orm.fields.LastModifiedByField` 🔒
     - `Last modified by <https://airtable.com/developers/web/api/field-model#lastmodifiedby>`__
   * - :class:`~pyairtable.orm.fields.LastModifiedTimeField` 🔒
     - `Last modified time <https://airtable.com/developers/web/api/field-model#lastmodifiedtime>`__
   * - :class:`~pyairtable.orm.fields.LinkField`
     - `Link to another record <https://airtable.com/developers/web/api/field-model#foreignkey>`__
   * - :class:`~pyairtable.orm.fields.LookupField` 🔒
     - `Lookup <https://airtable.com/developers/web/api/field-model#lookup>`__
   * - :class:`~pyairtable.orm.fields.MultipleAttachmentsField`
     - `Attachments <https://airtable.com/developers/web/api/field-model#multipleattachment>`__
   * - :class:`~pyairtable.orm.fields.MultipleCollaboratorsField`
     - `Multiple Collaborators <https://airtable.com/developers/web/api/field-model#multicollaborator>`__
   * - :class:`~pyairtable.orm.fields.MultipleSelectField`
     - `Multiple select <https://airtable.com/developers/web/api/field-model#multiselect>`__
   * - :class:`~pyairtable.orm.fields.NumberField`
     - `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__
   * - :class:`~pyairtable.orm.fields.PercentField`
     - `Percent <https://airtable.com/developers/web/api/field-model#percentnumber>`__
   * - :class:`~pyairtable.orm.fields.PhoneNumberField`
     - `Phone <https://airtable.com/developers/web/api/field-model#phone>`__
   * - :class:`~pyairtable.orm.fields.RatingField`
     - `Rating <https://airtable.com/developers/web/api/field-model#rating>`__
   * - :class:`~pyairtable.orm.fields.RichTextField`
     - `Rich text <https://airtable.com/developers/web/api/field-model#rich-text>`__
   * - :class:`~pyairtable.orm.fields.SelectField`
     - `Single select <https://airtable.com/developers/web/api/field-model#select>`__
   * - :class:`~pyairtable.orm.fields.TextField`
     - `Single line text <https://airtable.com/developers/web/api/field-model#simpletext>`__, `Long text <https://airtable.com/developers/web/api/field-model#multilinetext>`__
   * - :class:`~pyairtable.orm.fields.UrlField`
     - `Url <https://airtable.com/developers/web/api/field-model#urltext>`__
.. [[[end]]]


Formulas, Rollups, and Lookups
----------------------------------

The data type of "formula", "rollup", and "lookup" fields will depend on the underlying fields
they reference, and pyAirtable cannot easily guess at those fields' types.

If you need to refer to one of these fields in the ORM, you need to know what type of value
you expect it to contain. You can then declare that as a read-only field:

.. code-block:: python

    from pyairtable.orm import fields as F

    class MyTable(Model):
        class Meta: ...

        formula_field = F.TextField("My Formula", readonly=True)
        rollup_field = F.IntegerField("Row Count", readonly=True)
        lookup_field = F.LookupField[str]("My Lookup", readonly=True)


Linking Records
----------------

In addition to standard data type fields, the :class:`~pyairtable.orm.fields.LinkField`
class offers a special behaviour that can fetch linked records, so that you can
traverse between related records.

.. code-block:: python

    from pyairtable.orm import Model, fields as F as F

    class Company(Model):
        class Meta: ...

        name = F.TextField("Name")

    class Person(Model):
        class Meta: ...

        name = F.TextField("Name")
        company = F.LinkField("Company", Company)

.. code-block:: python

    >>> person = Person.from_id("recZ6qSLw0OCA61ul")
    >>> person.company
    [<Company id='recqSk20OCrB13lZ7'>]

.. note::
    Airtable's UI allows apps to restrict the user interface to choosing one record,
    rather than several; this appears as `prefersSingleRecordLink <https://airtable.com/developers/web/api/field-model#foreignkey-fieldtype-options-preferssinglerecordlink>`_
    in the `field configuration <https://airtable.com/developers/web/api/field-model>`__.
    However, the API will *always* return these fields as a list of record IDs, so
    pyAirtable will *always* represent link fields as a list (never a single model).


Cyclical links
""""""""""""""

If you need to model a link in two directions, or model a link to the same table,
you'll be creating a field before the linked model is created. You can pass a
fully qualified module and class name as a ``str`` instead:

.. code-block:: python

    from pyairtable.orm import Model, fields as F as F

    class Company(Model):
        class Meta: ...

        name = F.TextField("Name")
        employees = F.LinkField["Person"]("Employees", "module.name.Person")

    class Person(Model):
        class Meta: ...

        name = F.TextField("Name")
        company = F.LinkField("Company", Company)
        manager = F.LinkField["Person"]("Manager", "module.name.Person")

.. code-block:: python

    >>> person = Person.from_id("recZ6qSLw0OCA61ul")
    >>> person.manager
    [<Person id='recSLw0OCA61ulZ6q'>]
    >>> person.company[0].employees
    [<Person id='recZ6qSLw0OCA61ul'>, <Person id='recSLw0OCA61ulZ6q'>, ...]

Breaking down the :class:`~pyairtable.orm.fields.LinkField` invocation above,
there are four components:

.. code-block:: python

      manager = F.LinkField["Person"]("Manager", "module.name.Person")
     #^^^^^^^               ^^^^^^^^  ^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^
     #  (1)                    (2)       (3)             (4)

1. The name of the attribute on the model
2. Type annotation (optional, for mypy users)
3. Airtable's field name for the API
4. The fully qualified module and class name of the linked model


Limitations
"""""""""""

You cannot save a record via ORM unless you've first created all of its linked records:

    >>> alice = Person.from_id("recWcnG8712AqNuHw")
    >>> alice.manager = [Person()]
    >>> alice.save()
    Traceback (most recent call last):
      ...
    ValueError: Person.manager contains an unsaved record
