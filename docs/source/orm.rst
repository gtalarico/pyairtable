.. include:: substitutions.rst

ORM
==============


Defining Models
---------------

The :class:`~pyairtable.orm.Model` class allows you create ORM-style classes for your Airtable tables.

.. code-block:: python

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


Once you have a model, you can create new objects to represent your
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


Supported Field Types
-----------------------------

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
   * - :class:`~pyairtable.orm.fields.AttachmentsField`
     - `Attachments <https://airtable.com/developers/web/api/field-model#multipleattachment>`__
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


.. note::
    :class:`~pyairtable.orm.fields.LookupField` will always return a list of values,
    even if there is only a single value shown in the Airtable UI.


Error Values
------------

Airtable will return special values to represent errors from invalid formulas,
division by zero, or other sorts of issues. These will be returned by the ORM as-is.
Read more at `Common formula errors and how to fix them <https://support.airtable.com/docs/common-formula-errors-and-how-to-fix-them>`_.

You can check for errors using the :func:`~pyairtable.api.types.is_airtable_error` function:

  >>> record = MyTable.from_id("recyhb9UNkEMaZtYA")
  >>> record.formula_field
  {'error': '#ERROR!'}
  >>> record.rollup_field
  {'specialValue': 'NaN'}
  >>> record.lookup_field
  [{'error': '#ERROR!'}]
  >>> from pyairtable.api.types import is_airtable_error
  >>> is_airtable_error(record.formula_field)
  True
  >>> is_airtable_error(record.rollup_field)
  True
  >>> is_airtable_error(record.lookup_field[0])
  True


Linked Records
----------------

In addition to standard data type fields, the :class:`~pyairtable.orm.fields.LinkField`
class offers a special behaviour that can fetch linked records, so that you can
traverse between related records.

.. code-block:: python

    from pyairtable.orm import Model, fields as F

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
    >>> person.company[0].name
    'Acme Corp'

pyAirtable will not retrieve field values for a model's linked records until the
first time you access that field. So in the example above, the fields for Company
were loaded when ``person.company`` was called for the first time. After that,
the Company models are persisted, and won't be refreshed until you call
:meth:`~pyairtable.orm.Model.fetch`.

.. note::
    :class:`~pyairtable.orm.fields.LinkField` will always return a list of values,
    even if there is only a single value shown in the Airtable UI. It will not
    respect the `prefersSingleRecordLink <https://airtable.com/developers/web/api/field-model#foreignkey-fieldtype-options-preferssinglerecordlink>`_
    field configuration option, because the API will *always* return linked fields
    as a list of record IDs.


Cyclical links
""""""""""""""

If you need to model bidirectional links between two tables, you'll need to create one of
the fields before the linked model is created. pyAirtable provides a few options to
address this:

1. You can provide a ``str`` that is the fully qualified module and class name.
   For example, ``model="your.module.Model"`` will import the ``Model`` class from ``your.module``.
2. You can provide a ``str`` that is *just* the class name, and it will be imported
   from the same module as the model class.
3. You can provide the sentinel value ``LinkSelf``, and the link field will point to
   the same model where the link field is created.

.. code-block:: python

    from pyairtable.orm import Model, fields as F

    class Company(Model):
        class Meta: ...

        name = F.TextField("Name")
        employees = F.LinkField("Employees", "path.to.Person")  # option 1

    class Person(Model):
        class Meta: ...

        name = F.TextField("Name")
        company = F.LinkField[Company]("Company", Company)
        manager = F.LinkField["Person"]("Manager", "Person")  # option 2
        reports = F.LinkField["Person"]("Reports", F.LinkSelf)  # option 3

.. code-block:: python

    >>> person = Person.from_id("recZ6qSLw0OCA61ul")
    >>> person.manager
    [<Person id='recSLw0OCA61ulZ6q'>]
    >>> person.manager[0].reports
    [<Person id='recZ6qSLw0OCA61ul'>, ...]
    >>> person.company[0].employees
    [<Person id='recZ6qSLw0OCA61ul'>, <Person id='recSLw0OCA61ulZ6q'>, ...]

Breaking down the :class:`~pyairtable.orm.fields.LinkField` invocation above,
there are four components:

.. code-block:: python

      manager = F.LinkField["Person"]("Manager", "path.to.Person")
     #^^^^^^^               ^^^^^^^^  ^^^^^^^^^  ^^^^^^^^^^^^^^^^
     #  (1)                    (2)       (3)           (4)

1. The name of the attribute on the model
2. Type annotation (optional, for mypy users)
3. Airtable's field name for the API
4. The model class, the path to the model class, or :data:`~pyairtable.orm.fields.LinkSelf`


ORM Limitations
------------------

Linked records don't get saved automatically
""""""""""""""""""""""""""""""""""""""""""""

pyAirtable will not attempt to recursively save any linked records. Because of this,
you cannot save a record via ORM unless you've first created all of its linked records:

    >>> alice = Person.from_id("recWcnG8712AqNuHw")
    >>> alice.manager = [Person()]
    >>> alice.save()
    Traceback (most recent call last):
      ...
    ValueError: Person.manager contains an unsaved record

Field values don't get refreshed after saving a record
""""""""""""""""""""""""""""""""""""""""""""""""""""""

pyAirtable will not refresh models when calling :meth:`~pyairtable.orm.Model.save`,
since certain field types (like :class:`~pyairtable.orm.fields.LinkField`) return
lists of objects which you might not want pyAirtable to modify or discard. If you
want to reload the values of all fields after saving (for example, to refresh the
value of formula fields) then you need to call :meth:`~pyairtable.orm.Model.fetch`.

For example:

.. code-block:: python

    class Person(Model):
        class Meta: ...

        name = F.TextField("Name")
        manager = F.LinkField["Person"]("Manager", "Person")
        # This field is a formula: {Manager} != BLANK()
        has_manager = F.IntegerField("Has Manager?", readonly=True)


    bob = Person.from_id("rec2AqNuHwWcnG871")
    assert bob.manager == []
    assert bob.has_manager == 0

    bob.manager = [alice]
    bob.save()
    assert bob.has_manager == 0

    bob.fetch()
    assert bob.has_manager == 1

Type annotations don't account for possible formula errors
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

The ORM module does its best to give meaningful type annotations for each field.
However, it is not feasible for the ORM to determine which fields' underlying types
might return an error code, and to annotate it accordingly.

Taking the same example as above...

.. code-block:: python

    class Person(Model):
        class Meta: ...

        name = F.TextField("Name")
        has_manager = F.IntegerField("Has Manager?", readonly=True)  # formula

...the type annotation of ``Person().has_manager`` will appear as ``int`` to mypy
and to most type-aware code editors. It is nonetheless possible that if the formula
becomes invalid, ``person.has_manager`` will return ``{'error': '#ERROR!'}``
(which is obviously not an ``int``).

In most cases you probably want your code to fail quickly and loudly if there is an
error value coming back from the Airtable API. In the unusual cases where you want
to gracefully handle an error and move on, use :func:`~pyairtable.api.types.is_airtable_error`.
