Using the Command Line
=======================

pyAirtable ships with a rudimentary command line interface for interacting with Airtable.
This does not have full support for all Airtable API endpoints, but it does provide a way
to interact with the most common use cases. It will usually output JSON.

CLI Quickstart
--------------

.. code-block:: shell

    % pip install 'pyairtable[cli]'
    % read -s AIRTABLE_API_KEY
    ...
    % export AIRTABLE_API_KEY
    % pyairtable whoami
    {"id": "usrXXXXXXXXXXXX", "email": "you@example.com"}
    % pyairtable base YOUR_BASE_ID table YOUR_TABLE_NAME records
    [{"id": "recXXXXXXXXXXXX", "fields": {...}}, ...]

Authentication
--------------

There are a few ways to pass your authentication information to the CLI:

1. Put your API key into the ``AIRTABLE_API_KEY`` environment variable.
   If you need to use a different variable name, you can pass the
   appropriate variable name with the ``-ke/--key-env`` option.
2. Put your API key into a file, and put the full path to the file
   into the ``AIRTABLE_API_KEY_FILE`` environment variable.
   If you need to use a different variable name, you can pass the
   appropriate variable name with the ``-kf/--key-file`` option.
3. Pass the API key as an argument to the CLI. This is not recommended
   as it could be visible to other processes or stored in your shell history.
   If you must do it, use the ``-k/--key`` option.

Shortcuts
---------

If you pass a partial command to the CLI, it will try to match it to a full command.
This only works if there is a single unambiguous completion for the partial command.
For example, ``pyairtable e`` will be interpreted as ``pyairtable enterprise``,
but ``pyairtable b`` is ambiguous, as it could mean ``base`` or ``bases``.

Command list
------------

..  [[[cog
    from contextlib import redirect_stdout
    from io import StringIO
    from pyairtable.cli import cli, CLI_COMMANDS
    import textwrap

    for cmd in ["", *CLI_COMMANDS]:
        with redirect_stdout(StringIO()) as help_output:
            cli(
                ["-k", "fake", *cmd.split(), "--help"],
                prog_name="pyairtable",
                standalone_mode=False
            )
        if cmd:
            heading = " ".join(w for w in cmd.split() if w == w.lower())
            cog.outl()
            cog.outl(heading)
            cog.outl("~" * len(heading))
        cog.outl()
        cog.outl(".. code-block:: text")
        cog.outl()
        cog.outl(textwrap.indent(help_output.getvalue(), " " * 4))
    ]]]

.. code-block:: text

    Usage: pyairtable [OPTIONS] COMMAND [ARGS]...

    Options:
      -k, --key TEXT        Your API key.
      -kf, --key-file PATH  File containing your API key.
      -ke, --key-env VAR    Env var containing your API key.
      -v, --verbose         Print verbose output.
      --help                Show this message and exit.

    Commands:
      whoami                              Print the current user's information.
      bases                               List all available bases.
      base ID schema                      Print the base schema.
      base ID table ID_OR_NAME records    Retrieve records from the table.
      base ID table ID_OR_NAME schema     Print the table's schema as JSON.
      base ID collaborators               Print base collaborators.
      base ID shares                      Print base shares.
      base ID orm                         Generate a Python ORM module.
      enterprise ID info                  Print information about an enterprise.
      enterprise ID user ID_OR_EMAIL      Print one user's information.
      enterprise ID users ID_OR_EMAIL...  Print many users, keyed by user ID.
      enterprise ID group ID              Print a user group's information.
      enterprise ID groups ID...          Print many groups, keyed by group ID.


whoami
~~~~~~

.. code-block:: text

    Usage: pyairtable whoami [OPTIONS]

      Print the current user's information.

    Options:
      --help  Show this message and exit.


bases
~~~~~

.. code-block:: text

    Usage: pyairtable bases [OPTIONS]

      List all available bases.

    Options:
      --help  Show this message and exit.


base schema
~~~~~~~~~~~

.. code-block:: text

    Usage: pyairtable base BASE_ID schema [OPTIONS]

      Print the base schema.

    Options:
      --help  Show this message and exit.


base table records
~~~~~~~~~~~~~~~~~~

.. code-block:: text

    Usage: pyairtable base BASE_ID table ID_OR_NAME records [OPTIONS]

      Retrieve records from the table.

    Options:
      -f, --formula TEXT   Filter records with a formula.
      -v, --view TEXT      Filter records by a view.
      -n, --limit INTEGER  Limit the number of records returned.
      -S, --sort TEXT      Sort records by field(s).
      -F, --field TEXT     Limit output to certain field(s).
      --help               Show this message and exit.


base table schema
~~~~~~~~~~~~~~~~~

.. code-block:: text

    Usage: pyairtable base BASE_ID table ID_OR_NAME schema [OPTIONS]

      Print the table's schema as JSON.

    Options:
      --help  Show this message and exit.


base collaborators
~~~~~~~~~~~~~~~~~~

.. code-block:: text

    Usage: pyairtable base BASE_ID collaborators [OPTIONS]

      Print base collaborators.

    Options:
      --help  Show this message and exit.


base shares
~~~~~~~~~~~

.. code-block:: text

    Usage: pyairtable base BASE_ID shares [OPTIONS]

      Print base shares.

    Options:
      --help  Show this message and exit.


base orm
~~~~~~~~

.. code-block:: text

    Usage: pyairtable base BASE_ID orm [OPTIONS]

      Generate a Python ORM module.

    Options:
      -t, --table NAME_OR_ID  Only generate specific table(s).
      --help                  Show this message and exit.


enterprise info
~~~~~~~~~~~~~~~

.. code-block:: text

    Usage: pyairtable enterprise ENTERPRISE_ID info [OPTIONS]

      Print information about an enterprise.

    Options:
      --help  Show this message and exit.


enterprise user
~~~~~~~~~~~~~~~

.. code-block:: text

    Usage: pyairtable enterprise ENTERPRISE_ID user [OPTIONS] ID_OR_EMAIL

      Print one user's information.

    Options:
      --help  Show this message and exit.


enterprise users
~~~~~~~~~~~~~~~~

.. code-block:: text

    Usage: pyairtable enterprise ENTERPRISE_ID users [OPTIONS] ID_OR_EMAIL...

      Print many users, keyed by user ID.

    Options:
      -c, --collaborations  Include collaborations.
      -a, --all             Retrieve all users.
      --help                Show this message and exit.


enterprise group
~~~~~~~~~~~~~~~~

.. code-block:: text

    Usage: pyairtable enterprise ENTERPRISE_ID group [OPTIONS] GROUP_ID

      Print a user group's information.

    Options:
      --help  Show this message and exit.


enterprise groups
~~~~~~~~~~~~~~~~~

.. code-block:: text

    Usage: pyairtable enterprise ENTERPRISE_ID groups [OPTIONS] GROUP_ID...

      Print many groups, keyed by group ID.

    Options:
      -a, --all             Retrieve all groups.
      -c, --collaborations  Include collaborations.
      --help                Show this message and exit.

.. [[[end]]] (checksum: 9181d3a8abea1b24cb46cb6e997b08f0)
