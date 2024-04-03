.. include:: _warn_latest.rst
.. include:: _substitutions.rst


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
        company = F.SingleLinkField("Company", Company, lazy=False)

        class Meta:
            base_id = "appaPqizdsNHDvlEm"
            table_name = "Contact"
            api_key = "keyapikey"


Once you have a model, you can query for existing records using the
``first()`` and ``all()`` methods, which take the same arguments as
:meth:`Table.first <pyairtable.Table.first>` and :meth:`Table.all <pyairtable.Table.all>`.

You can also create new objects to represent Airtable records you wish
to create and save. Call :meth:`~pyairtable.orm.Model.save` to save the
newly created object back to Airtable.

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

Use :meth:`~pyairtable.orm.Model.delete` to delete the record:

    >>> contact.delete()
    True

There are also :meth:`~pyairtable.orm.Model.batch_save` and
:meth:`~pyairtable.orm.Model.batch_delete` for when you need to
create, modify, or delete several records at once:

    >>> contacts = Contact.all()
    >>> contacts.append(Contact(first_name="Alice", email="alice@example.com"))
    >>> Contact.batch_save(contacts)
    >>> Contact.batch_delete(contacts)

You can use your model's fields in :doc:`formula expressions <formulas>`.
ORM models' fields also provide shortcut methods
:meth:`~pyairtable.orm.fields.Field.eq`,
:meth:`~pyairtable.orm.fields.Field.ne`,
:meth:`~pyairtable.orm.fields.Field.gt`,
:meth:`~pyairtable.orm.fields.Field.gte`,
:meth:`~pyairtable.orm.fields.Field.lt`, and
:meth:`~pyairtable.orm.fields.Field.lte`:

    >>> formula = Contact.last_name.eq("Smith") & Contact.is_registered
    >>> str(formula)
    "AND({Last Name}='Smith', {Registered})"
    >>> results = Contact.all(formula=formula)
    [...]


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

    def cog_class_table(classes):
        cog.outl(".. list-table::")
        cog.outl("   :header-rows: 1\n")
        cog.outl("   * - ORM field class")
        cog.outl("     - Airtable field type(s)")
        for cls in classes:
            links = re.findall(r"`.+? <.*?field-model.*?>`", cls.__doc__ or "")
            ro = ' 🔒' if cls.readonly else ''
            cog.outl(f"   * - :class:`~pyairtable.orm.fields.{cls.__name__}`{ro}")
            cog.outl(f"     - {', '.join(f'{link}__' for link in links) if links else '(see docs)'}")

    classes = sorted(fields.ALL_FIELDS, key=attrgetter("__name__"))
    optional = [cls for cls in classes if not cls.__name__.startswith("Required")]
    required = [cls for cls in classes if cls.__name__.startswith("Required")]

    cog.outl("..")  # terminate the comment block
    cog_class_table(optional)
    cog.outl("")
    cog.outl("Airtable does not have a concept of fields that require values,")
    cog.outl("but pyAirtable allows you to enforce that concept within code")
    cog.outl("using one of the following field classes.")
    cog.outl("")
    cog.outl("See :ref:`Required Values` for more details.")
    cog.outl("")
    cog_class_table(required)
    ]]]
..
.. list-table::
   :header-rows: 1

   * - ORM field class
     - Airtable field type(s)
   * - :class:`~pyairtable.orm.fields.AITextField` 🔒
     - `AI Text <https://airtable.com/developers/web/api/field-model#aitext>`__
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
   * - :class:`~pyairtable.orm.fields.SingleLinkField`
     - `Link to another record <https://airtable.com/developers/web/api/field-model#foreignkey>`__
   * - :class:`~pyairtable.orm.fields.TextField`
     - `Single line text <https://airtable.com/developers/web/api/field-model#simpletext>`__, `Long text <https://airtable.com/developers/web/api/field-model#multilinetext>`__
   * - :class:`~pyairtable.orm.fields.UrlField`
     - `Url <https://airtable.com/developers/web/api/field-model#urltext>`__

Airtable does not have a concept of fields that require values,
but pyAirtable allows you to enforce that concept within code
using one of the following field classes.

See :ref:`Required Values` for more details.

.. list-table::
   :header-rows: 1

   * - ORM field class
     - Airtable field type(s)
   * - :class:`~pyairtable.orm.fields.RequiredAITextField` 🔒
     - `AI Text <https://airtable.com/developers/web/api/field-model#aitext>`__
   * - :class:`~pyairtable.orm.fields.RequiredBarcodeField`
     - `Barcode <https://airtable.com/developers/web/api/field-model#barcode>`__
   * - :class:`~pyairtable.orm.fields.RequiredCollaboratorField`
     - `Collaborator <https://airtable.com/developers/web/api/field-model#collaborator>`__
   * - :class:`~pyairtable.orm.fields.RequiredCountField` 🔒
     - `Count <https://airtable.com/developers/web/api/field-model#count>`__
   * - :class:`~pyairtable.orm.fields.RequiredCurrencyField`
     - `Currency <https://airtable.com/developers/web/api/field-model#currencynumber>`__
   * - :class:`~pyairtable.orm.fields.RequiredDateField`
     - `Date <https://airtable.com/developers/web/api/field-model#dateonly>`__
   * - :class:`~pyairtable.orm.fields.RequiredDatetimeField`
     - `Date and time <https://airtable.com/developers/web/api/field-model#dateandtime>`__
   * - :class:`~pyairtable.orm.fields.RequiredDurationField`
     - `Duration <https://airtable.com/developers/web/api/field-model#durationnumber>`__
   * - :class:`~pyairtable.orm.fields.RequiredEmailField`
     - `Email <https://airtable.com/developers/web/api/field-model#email>`__
   * - :class:`~pyairtable.orm.fields.RequiredFloatField`
     - `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__
   * - :class:`~pyairtable.orm.fields.RequiredIntegerField`
     - `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__
   * - :class:`~pyairtable.orm.fields.RequiredNumberField`
     - `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__
   * - :class:`~pyairtable.orm.fields.RequiredPercentField`
     - `Percent <https://airtable.com/developers/web/api/field-model#percentnumber>`__
   * - :class:`~pyairtable.orm.fields.RequiredPhoneNumberField`
     - `Phone <https://airtable.com/developers/web/api/field-model#phone>`__
   * - :class:`~pyairtable.orm.fields.RequiredRatingField`
     - `Rating <https://airtable.com/developers/web/api/field-model#rating>`__
   * - :class:`~pyairtable.orm.fields.RequiredRichTextField`
     - `Rich text <https://airtable.com/developers/web/api/field-model#rich-text>`__
   * - :class:`~pyairtable.orm.fields.RequiredSelectField`
     - `Single select <https://airtable.com/developers/web/api/field-model#select>`__
   * - :class:`~pyairtable.orm.fields.RequiredTextField`
     - `Single line text <https://airtable.com/developers/web/api/field-model#simpletext>`__, `Long text <https://airtable.com/developers/web/api/field-model#multilinetext>`__
   * - :class:`~pyairtable.orm.fields.RequiredUrlField`
     - `Url <https://airtable.com/developers/web/api/field-model#urltext>`__
.. [[[end]]] (checksum: 131138e1071ba71d4f46f05da4d57570)


Formula, Rollup, and Lookup Fields
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


Required Values
---------------

Airtable does not generally have a concept of fields that require values, but
pyAirtable allows you to enforce that a field must have a value before saving it.
To do this, use one of the "Required" field types, which will raise an exception
if either of the following occur:

  1. If you try to set its value to ``None`` (or, sometimes, to the empty string).
  2. If the API returns a ``None`` (or empty string) as the field's value.

For example, given this code:

.. code-block:: python

    from pyairtable.orm import Model, fields as F

    class MyTable(Model):
        class Meta:
            ...

        name = F.RequiredTextField("Name")

The following will all raise an exception:

.. code-block:: python

    >>> MyTable(name=None)
    Traceback (most recent call last):
      ...
    MissingValue: MyTable.name does not accept empty values

    >>> r = MyTable.from_record(fake_record(Name="Alice"))
    >>> r.name
    'Alice'
    >>> r.name = None
    Traceback (most recent call last):
      ...
    MissingValue: MyTable.name does not accept empty values

    >>> r = MyTable.from_record(fake_record(Name=None))
    >>> r.name
    Traceback (most recent call last):
      ...
    MissingValue: MyTable.name received an empty value

One reason to use these fields (sparingly!) might be to avoid adding defensive
null-handling checks all over your code, if you are confident that the workflows
around your Airtable base will not produce an empty value (or that an empty value
is enough of a problem that your code should raise an exception).

Linked Records
----------------

In addition to standard data type fields, the :class:`~pyairtable.orm.fields.LinkField`
and :class:`~pyairtable.orm.fields.SingleLinkField` classes will fetch linked records
upon access, so that you can traverse between related records.

.. code-block:: python

    from pyairtable.orm import Model, fields as F

    class Person(Model):
        class Meta: ...

        name = F.TextField("Name")
        company = F.SingleLinkField("Company", "Company")

    class Company(Model):
        class Meta: ...

        name = F.TextField("Name")
        people = F.LinkField("People", Person)


.. code-block:: python

    >>> person = Person.from_id("recZ6qSLw0OCA61ul")
    >>> person.company
    <Company id='recqSk20OCrB13lZ7'>
    >>> person.company.name
    'Acme Corp'
    >>> person.company.people
    [<Person id='recZ6qSLw0OCA61ul'>, ...]

pyAirtable will not retrieve field values for a model's linked records until the
first time you access a field. So in the example above, the fields for Company
were loaded when ``person.company`` was called for the first time. Linked models
are persisted after being created, and won't be refreshed until you call
:meth:`~pyairtable.orm.Model.fetch`.

.. note::
    :class:`~pyairtable.orm.fields.LinkField` will always return a list of values,
    even if there is only a single value shown in the Airtable UI. It will not
    respect the `prefersSingleRecordLink <https://airtable.com/developers/web/api/field-model#foreignkey-fieldtype-options-preferssinglerecordlink>`_
    field configuration option. If you expect a field to only ever return a single
    linked record, use :class:`~pyairtable.orm.fields.SingleLinkField`.


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
        company = F.SingleLinkField[Company]("Company", Company)
        manager = F.SingleLinkField["Person"]("Manager", "Person")  # option 2
        reports = F.LinkField["Person"]("Reports", F.LinkSelf)  # option 3

.. code-block:: python

    >>> person = Person.from_id("recZ6qSLw0OCA61ul")
    >>> person.manager
    <Person id='recSLw0OCA61ulZ6q'>
    >>> person.manager.reports
    [<Person id='recZ6qSLw0OCA61ul'>, ...]
    >>> person.company.employees
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


Memoizing linked records
"""""""""""""""""""""""""""""

There are cases where your application may need to retrieve hundreds of nested
models through the ORM, and you don't want to make hundreds of Airtable API calls.
pyAirtable provides a way to pre-fetch and memoize instances for each record,
which will then be reused later by record link fields.

The usual way to do this is passing ``memoize=True`` to a retrieval method
at the beginning of your code to pre-fetch any records you might need.
For example, you might have the following:

.. code-block:: python

    from pyairtable.orm import Model, fields as F
    from operator import attrgetter

    class Book(Model):
        class Meta: ...
        title = F.TextField("Title")
        published = F.DateField("Publication Date")

    class Author(Model):
        class Meta: ...
        name = F.TextField("Name")
        books = F.LinkField("Books", Book)

    def main():
        books = Book.all(memoize=True)
        authors = Author.all(memoize=True)
        for author in authors:
            print(f"* {author.name}")
            for book in sorted(author.books, key=attrgetter("published")):
                print(f"  - {book.title} ({book.published.isoformat()})")

This code will perform a series of API calls at the beginning to fetch
all records from the Books and Authors tables, so that ``author.books``
does not need to request linked records one at a time during the loop.

You can also set ``memoize = True`` in the ``Meta`` configuration for your model,
which indicates that you always want to memoize models retrieved from the API:

.. code-block:: python

    class Book(Model):
        Meta = {..., "memoize": True}
        title = F.TextField("Title")

    class Author(Model):
        Meta = {...}
        name = F.TextField("Name")
        books = F.LinkField("Books", Book)

    Book.first()  # this will memoize the object it creates
    Author.first().books  # this will memoize all objects created
    Book.all(memoize=False)  # this will skip memoization

The following methods support the ``memoize=`` keyword argument.
You can pass ``memoize=False`` to override memoization that is
enabled on the model configuration.

   * :meth:`Model.all <pyairtable.orm.Model.all>`
   * :meth:`Model.first <pyairtable.orm.Model.first>`
   * :meth:`Model.from_record <pyairtable.orm.Model.from_record>`
   * :meth:`Model.from_id <pyairtable.orm.Model.from_id>`
   * :meth:`Model.from_ids <pyairtable.orm.Model.from_ids>`
   * :meth:`LinkField.populate <pyairtable.orm.fields.LinkField.populate>`
   * :meth:`SingleLinkField.populate <pyairtable.orm.fields.SingleLinkField.populate>`


Comments
----------

You can use :meth:`Model.comments <pyairtable.orm.Model.comments>` and
:meth:`Model.add_comment <pyairtable.orm.Model.add_comment>` to interact with
comments on a particular record, just like their :class:`~pyairtable.Table` equivalents:

    >>> record = YourModel.from_id("recMNxslc6jG0XedV")
    >>> comment = record.add_comment("Hello, @[usrVMNxslc6jG0Xed]!")
    >>> record.comments()
    [
        Comment(
            id='comdVMNxslc6jG0Xe',
            text='Hello, @[usrVMNxslc6jG0Xed]!',
            created_time=datetime.datetime(...),
            last_updated_time=None,
            mentioned={
                'usrVMNxslc6jG0Xed': Mentioned(
                    display_name='Alice',
                    email='alice@example.com',
                    id='usrVMNxslc6jG0Xed',
                    type='user'
                )
            },
            author=Collaborator(
                id='usr0000pyairtable',
                email='pyairtable@example.com',
                name='Your pyairtable access token'
            )
        )
    ]
    >>> comment.text = "Never mind!"
    >>> comment.save()
    >>> record.comments()[0].text
    'Never mind!'
    >>> comment.delete()


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

    from pyairtable.orm import fields as F

    class Person(Model):
        class Meta: ...

        name = F.TextField("Name")
        manager = F.SingleLinkField["Person"]("Manager", F.LinkSelf)
        # This field is a formula: {Manager} != BLANK()
        has_manager = F.IntegerField("Has Manager?", readonly=True)


    bob = Person.from_id("rec2AqNuHwWcnG871")
    assert bob.manager is None
    assert bob.has_manager == 0

    alice = Person.from_id("recAB2AqNuHwWcnG8")
    bob.manager = alice
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
