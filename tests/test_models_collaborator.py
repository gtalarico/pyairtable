import pytest

from pyairtable.models import Collaborator

fake_user_data = {
    "id": "usr000000fakeuser",
    "email": "fake@example.com",
    "name": "Fake User",
}


def test_parse():
    user = Collaborator.parse_obj(fake_user_data)
    assert user.id == fake_user_data["id"]
    assert user.email == fake_user_data["email"]
    assert user.name == fake_user_data["name"]


def test_init():
    c = Collaborator(id="usrXXXXXXXXXXXXX")
    assert c.id == "usrXXXXXXXXXXXXX"
    assert c.email is None
    assert c.name is None

    with pytest.raises(ValueError):
        Collaborator()

    with pytest.raises(ValueError):
        Collaborator(name="Fake User")
