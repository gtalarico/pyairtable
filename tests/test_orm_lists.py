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
                    "url": "https://example.com/a.txt",
                    "filename": "a.txt",
                    "type": "text/plain",
                },
            ],
            # Test that, if Airtable's API returns multiple fields (for some reason),
            # we will only use the first field in the "fields" key (not all of them).
            fake_id("fld"): [
                {
                    "id": fake_id("att"),
                    "url": "https://example.com/b.png",
                    "filename": "b.png",
                    "type": "image/png",
                },
            ],
        },
    }
    with mock.patch("pyairtable.Table.upload_attachment", return_value=response) as m:
        yield m


@pytest.mark.parametrize("content", [b"Hello, world!", "Hello, world!"])
def test_attachment_upload(mock_upload, tmp_path, content):
    """
    Test that we can add an attachment to a record.
    """
    fp = tmp_path / "a.txt"
    writer = fp.write_text if isinstance(content, str) else fp.write_bytes
    writer(content)

    record = fake_record()
    instance = Fake.from_record(record)
    instance.attachments.upload(fp)
    assert instance.attachments == [
        {
            "id": mock.ANY,
            "url": "https://example.com/a.txt",
            "filename": "a.txt",
            "type": "text/plain",
        },
    ]

    mock_upload.assert_called_once_with(
        record["id"],
        "Files",
        filename=fp,
        content=None,
        content_type=None,
    )


def test_attachment_upload__readonly(mock_upload):
    """
    Test that calling upload() on a readonly field will raise an exception.
    """
    record = fake_record()
    instance = Fake.from_record(record)
    with pytest.raises(ReadonlyFieldError):
        instance.readonly_attachments.upload("a.txt", content="Hello, world!")


def test_attachment_upload__unsaved_record(mock_upload):
    """
    Test that calling upload() on an unsaved record will not call the API
    and instead raises an exception.
    """
    instance = Fake()
    with pytest.raises(UnsavedRecordError):
        instance.attachments.upload("a.txt", content=b"Hello, world!")
    mock_upload.assert_not_called()


def test_attachment_upload__unsaved_value(mock_upload):
    """
    Test that calling upload() on an attachment list will clobber
    any other unsaved changes made to that field.

    This is not necessarily the most useful side effect, but it's the
    only rational way to deal with the fact that Airtable will return
    the full field value in its response, with no straightforward way
    for us to identify the specific attachment that was uploaded.
    """
    instance = Fake.from_record(fake_record())
    unsaved_url = "https://example.com/unsaved.txt"
    instance.attachments = [{"url": unsaved_url}]
    instance.attachments.upload("b.txt", content="Hello, world!")
    mock_upload.assert_called_once()
    assert len(instance.attachments) == 1
    assert instance.attachments[0]["url"] != unsaved_url
