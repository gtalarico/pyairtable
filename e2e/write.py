"""
End-to-end tests against
https://airtable.com/appaPqizdsNHDvlEm/tblfbOcVkVnnKxurq/viwhi8Qtuw2psSdGG?blocks=hide
"""

import os
from datetime import datetime

from pyairtable import Table
from pyairtable.utils import date_to_iso_str, datetime_to_iso_str

apikey = os.environ["AIRTABLE_KEY"]
base_id = "appaPqizdsNHDvlEm"
table_name = "TEST_TABLE"
table = Table(apikey, base_id, table_name)

table.create(
    {
        "text": "Some Text",
        "number": 5,
        "boolean": True,
        "phone": "540-123-4567",
        "date": date_to_iso_str(datetime.now()),
        "datetime": datetime_to_iso_str(datetime.now()),
    }
)
