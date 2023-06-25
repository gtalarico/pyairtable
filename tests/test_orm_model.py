import pytest

from pyairtable.orm import Model
from pyairtable.orm import fields as f
from pyairtable.testing import fake_meta, fake_record


def test_model_missing_meta():
    """
    Test that we throw an exception if Meta is missing.
    """
    with pytest.raises(AttributeError):

        class Address(Model):
            street = f.TextField("Street")


def test_model_missing_meta_attribute():
    """
    Test that we throw an exception if Meta is missing a required attribute.
    """
    with pytest.raises(ValueError):

        class Address(Model):
            street = f.TextField("Street")

            class Meta:
                base_id = "required"
                table_name = "required"
                # api_key = "required"


def test_model_empty_meta():
    """
    Test that we throw an exception when a required Meta attribute is None.
    """
    with pytest.raises(ValueError):

        class Address(Model):
            Meta = fake_meta(api_key=None)
            street = f.TextField("Street")


def test_model_overlapping():
    # Should raise error because conflicts with .exists()
    with pytest.raises(ValueError):

        class Address(Model):
            Meta = fake_meta()
            exists = f.TextField("Exists")  # clases with Model.exists()


def test_repr():
    class Contact(Model):
        Meta = fake_meta()

    record = fake_record()
    assert repr(Contact.from_record(record)) == f"<Contact id='{record['id']}'>"
    assert repr(Contact()) == "<unsaved Contact>"
