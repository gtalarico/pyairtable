import airtable.__version__ as ver


def test_version():
    assert isinstance(ver.__version__, str)
