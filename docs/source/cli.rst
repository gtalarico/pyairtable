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

Command list
------------

..  [[[cog
    from contextlib import redirect_stdout
    from io import StringIO
    from pyairtable.cli import cli
    import textwrap

    cog.outl()

    indent = " " * 4
    commands = [
        "--help",
        "base --help",
        "base BASE_ID table --help",
        "base BASE_ID table TABLE_NAME records --help",
    ]
    for cmd in commands:
        with redirect_stdout(StringIO()) as f:
            cli(
                ["-k", "fake", *cmd.split()],
                prog_name="pyairtable",
                standalone_mode=False
            )

        cog.outl(".. code-block:: shell")
        cog.outl()
        cog.outl(f"{indent}% pyairtable {cmd}")
        cog.outl(textwrap.indent(f.getvalue(), indent))
    ]]]

.. code-block:: shell

    % pyairtable --help
    Usage: pyairtable [OPTIONS] COMMAND [ARGS]...

    Options:
      -k, --key TEXT        Your API key.
      -kf, --key-file PATH  File containing your API key.
      -ke, --key-env VAR    Env var containing your API key.
      --help                Show this message and exit.

    Commands:
      base    Print information about a base.
      bases   List all available bases.
      whoami  Print information about the current user.

.. code-block:: shell

    % pyairtable base --help
    Usage: pyairtable base [OPTIONS] BASE_ID COMMAND [ARGS]...

      Print information about a base.

    Options:
      --help  Show this message and exit.

    Commands:
      orm     Print a Python module with ORM models.
      schema  Print the base schema.
      table   Print information about a table.

.. code-block:: shell

    % pyairtable base BASE_ID table --help
    Usage: pyairtable base BASE_ID table [OPTIONS] ID_OR_NAME COMMAND [ARGS]...

      Print information about a table.

    Options:
      --help  Show this message and exit.

    Commands:
      records  Retrieve records from the table.
      schema   Print a JSON representation of the table schema.

.. code-block:: shell

    % pyairtable base BASE_ID table TABLE_NAME records --help
    Usage: pyairtable base BASE_ID table ID_OR_NAME records [OPTIONS]

      Retrieve records from the table.

    Options:
      -f, --formula TEXT   Filter records with a formula.
      -v, --view TEXT      Filter records by a view.
      -n, --limit INTEGER  Limit the number of records returned.
      -S, --sort TEXT      Sort records by field(s).
      -F, --field TEXT     Limit output to certain field(s).
      --help               Show this message and exit.

.. [[[end]]] (checksum: 320534bcf1749b598527336a32ec0c01)
