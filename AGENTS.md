# AGENTS.md

Read all developer instructions and contribution guidelines in @README.md.

## Testing your changes

When changing code in `pyairtable/`, follow these steps one at a time:

1. `tox -e mypy`
2. `tox -e py314 -- $CHANGED_FILE $CORRESPONDING_TEST_FILE`
3. `tox -e coverage`
4. `make lint`
5. `make docs`
6. `make test`

When changing code in `docs/`, follow these steps instead:

1. `make docs`
2. `make lint`
