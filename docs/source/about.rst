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
   # Create Virtual Environment
   python3 -m venv .venv
   source .venv/bin/activate
   make setup # Sets up githooks and install package and depedencies
   make test # run test complete suite
   # Optional, use as needed
   make lint # lints locally - also done in pre-merge CI
   make docs # builds docs locally - see `docs/build/index.html`


Release
-------

.. code-block:: bash

   make bump


License
*******
`MIT License <https://opensource.org/licenses/MIT>`_
