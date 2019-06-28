import json

import pytest
from mock import Mock
from requests import HTTPError


def http_error_with_url():
    raise HTTPError("unable to process page%20url")


def json_decoder_error():
    raise ValueError()


def test_error_mesg_in_json(table, response):
    response.status_code = 400
    response.json = Mock(return_value={"error": "here's what went wrong"})
    with pytest.raises(HTTPError) as e:
        table._process_response(response)
    assert str(e).endswith("Not Found [Error: here's what went wrong]")


def test_error_without_mesg_in_json(table, response):
    response.status_code = 404
    response.json = Mock(return_value={})
    with pytest.raises(HTTPError) as e:
        table._process_response(response)
    assert str(e).endswith("Not Found")


def test_non_422_error_with_json_decode_error(table, response):
    response.status_code = 400
    response.json.side_effect = json.decoder.JSONDecodeError('', '', 0)
    with pytest.raises(HTTPError):
        table._process_response(response)
