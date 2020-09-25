import os
from airtable import Airtable

test_base = "appaPqizdsNHDvlEm"
test_table = "table"
airtable = Airtable(test_base, test_table, api_key=os.environ["AIRTABLE_API_KEY"])

# Insert
rec = airtable.insert({"text": "A", "number": 1, "boolean": True})

# Get
assert airtable.get(rec["id"])

# Update
rv = airtable.update(rec["id"], {"text": "B"})
assert rv["fields"]["text"] == "B"

# Replace
rv = airtable.replace(rec["id"], {"text": "C"})
assert rv["fields"]["text"] == "C"

# Get all
assert airtable.get_all()

# Delete
assert airtable.delete(rec["id"])


# Batch Insert
records = airtable.batch_insert(
    [{"text": "A", "number": 1, "boolean": True} for _ in range(100)]
)

# Batch Delete
records = airtable.batch_delete([r["id"] for r in records])
assert len(records) == 100

