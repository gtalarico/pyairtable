import pytest
from mock import Mock
from requests import HTTPError


def test_error_mesg_in_json(table, response):
    response.status_code = 400
    response.json = Mock(return_value={"error": "here's what went wrong"})
    with pytest.raises(HTTPError):
        table._process_response(response)


def test_error_without_mesg_in_json(table, response):
    response.status_code = 404
    response.json = Mock(return_value={})
    with pytest.raises(HTTPError):
        table._process_response(response)


def test_non_422_error_with_json_decode_error(table, response):
    response.status_code = 400
    response.json.side_effect = ValueError
    with pytest.raises(HTTPError):
        table._process_response(response)
