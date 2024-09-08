from datetime import datetime, timezone
from unittest import mock

import pytest

from pyairtable.exceptions import ReadonlyFieldError, UnsavedRecordError
from pyairtable.orm import fields as F
from pyairtable.orm.model import Model
from pyairtable.testing import fake_id, fake_meta, fake_record

NOW = datetime.now(timezone.utc).isoformat()


class Fake(Model):
    Meta = fake_meta()
    attachments = F.AttachmentsField("Files")
    readonly_attachments = F.AttachmentsField("Other Files", readonly=True)


@pytest.fixture
def mock_upload():
    response = {
        "id": fake_id(),
        "createdTime": NOW,
        "fields": {
            fake_id("fld"): [
                {
                    "id": fake_id("att"),
                    "url": "https://example.com/a.png",
                    "filename": "a.txt",
                    "type": "text/plain",
                },
            ]
        },
    }
    with mock.patch("pyairtable.Table.upload_attachment", return_value=response) as m:
        yield m


def test_attachment_upload(mock_upload, tmp_path):
    """
    Test that we can add an attachment to a record.
    """
    tmp_file = tmp_path / "a.txt"
    tmp_file.write_text("Hello, world!")

    record = fake_record()
    instance = Fake.from_record(record)
    instance.attachments.upload(tmp_file)

    mock_upload.assert_called_once_with(
        record["id"],
        "Files",
        filename=tmp_file,
        content=None,
        content_type=None,
    )


def test_attachment_upload__readonly(mock_upload):
    record = fake_record()
    instance = Fake.from_record(record)
    with pytest.raises(ReadonlyFieldError):
        instance.readonly_attachments.upload("a.txt", content="Hello, world!")


def test_attachment_upload__unsaved(mock_upload):
    instance = Fake()
    with pytest.raises(UnsavedRecordError):
        instance.attachments.upload("a.txt", content=b"Hello, world!")
    mock_upload.assert_not_called()
