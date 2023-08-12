import pytest

from pyairtable.api.enterprise import Enterprise


@pytest.fixture
def enterprise(api):
    return Enterprise(api, "entUBq2RGdihxl3vU")


def test_info(enterprise, requests_mock, sample_json):
    m = requests_mock.get(enterprise.url, json=sample_json("Enterprise"))
    assert enterprise.info().id == "entUBq2RGdihxl3vU"
    assert enterprise.info().workspace_ids == ["wspmhESAta6clCCwF", "wspHvvm4dAktsStZH"]
    assert enterprise.info().email_domains[0].is_sso_required is True
    assert m.call_count == 1

    assert enterprise.info(force=True).id == "entUBq2RGdihxl3vU"
    assert m.call_count == 2
