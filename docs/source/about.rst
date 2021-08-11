About
=====


Questions
*********
Post them over in the project's `Github Page <http://www.github.com/gtalarico/pyairtable>`_

_______________________________________________

Contribute
**********

.. code-block:: python

   git clone git@github.com:gtalarico/pyairtable.git
   cd pyairtable
   pip install -e .
   make docs # builds docs locally - see `docs/build/index.html`
   make lint # lints
   make test # run test complete suite

.. warning::
   ``make test`` includes some unmocked integration tests that require access to a particular Airtable.
   You can skip those test using `pytest -m 'not integration'`


License
*******
`MIT License <https://opensource.org/licenses/MIT>`_
