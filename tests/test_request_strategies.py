import pytest
from pyairtable.api import Api, Table, Base
from pyairtable.request_strategies import RequestStrategy, SimpleRequestStrategy


def test_request_strategy_initialize(request_strategy, invalid_request_strategy):
    # When passed a valid class should instantiate it
    _request_strategy = RequestStrategy.initialize(SimpleRequestStrategy)
    assert isinstance(_request_strategy, SimpleRequestStrategy)
    # When passed a valid instance should return it
    _request_strategy_2 = RequestStrategy.initialize(request_strategy)
    assert isinstance(_request_strategy_2, SimpleRequestStrategy)
    assert _request_strategy_2 is request_strategy
    # When passed anything else, it should error
    with pytest.raises(TypeError):
        RequestStrategy.initialize(invalid_request_strategy)  # type: ignore


def test_api_has_default_request_strategy(api):
    assert hasattr(api, "request_strategy")
    assert isinstance(api.request_strategy, SimpleRequestStrategy)


def test_base_has_default_request_strategy(base):
    assert hasattr(base, "request_strategy")
    assert isinstance(base.request_strategy, SimpleRequestStrategy)


def test_table_has_default_request_strategy(table):
    assert hasattr(table, "request_strategy")
    assert isinstance(table.request_strategy, SimpleRequestStrategy)


def test_api_accepts_request_strategy_class(constants):
    api = Api(constants["API_KEY"], request_strategy=SimpleRequestStrategy)
    assert hasattr(api, "request_strategy")
    assert isinstance(api.request_strategy, SimpleRequestStrategy)
    assert not isinstance(api.request_strategy, type)


def test_base_accepts_request_strategy_class(constants):
    base = Base(
        constants["API_KEY"],
        constants["BASE_ID"],
        request_strategy=SimpleRequestStrategy,
    )
    assert hasattr(base, "request_strategy")
    assert isinstance(base.request_strategy, SimpleRequestStrategy)
    assert not isinstance(base.request_strategy, type)


def test_table_accepts_request_strategy_class(constants):
    table = Table(
        constants["API_KEY"],
        constants["BASE_ID"],
        constants["TABLE_NAME"],
        request_strategy=SimpleRequestStrategy,
    )
    assert hasattr(table, "request_strategy")
    assert isinstance(table.request_strategy, SimpleRequestStrategy)
    assert not isinstance(table.request_strategy, type)


def test_api_accepts_request_strategy_instance(constants, request_strategy):
    api = Api(constants["API_KEY"], request_strategy=request_strategy)
    assert hasattr(api, "request_strategy")
    assert isinstance(api.request_strategy, SimpleRequestStrategy)
    assert api.request_strategy is request_strategy


def test_base_accepts_request_strategy_instance(constants, request_strategy):
    base = Base(
        constants["API_KEY"],
        constants["BASE_ID"],
        request_strategy=request_strategy,
    )
    assert hasattr(base, "request_strategy")
    assert isinstance(base.request_strategy, SimpleRequestStrategy)
    assert base.request_strategy is request_strategy


def test_table_accepts_request_strategy_instance(constants, request_strategy):
    table = Table(
        constants["API_KEY"],
        constants["BASE_ID"],
        constants["TABLE_NAME"],
        request_strategy=request_strategy,
    )
    assert hasattr(table, "request_strategy")
    assert isinstance(table.request_strategy, SimpleRequestStrategy)
    assert table.request_strategy is request_strategy


def test_api_rejects_invalid_request_strategy(constants, invalid_request_strategy):
    with pytest.raises(TypeError):
        Api(constants["API_KEY"], request_strategy=invalid_request_strategy)


def test_base_rejects_invalid_request_strategy(constants, invalid_request_strategy):
    with pytest.raises(TypeError):
        Base(
            constants["API_KEY"],
            constants["BASE_ID"],
            request_strategy=invalid_request_strategy,
        )


def test_table_rejects_invalid_request_strategy(constants, invalid_request_strategy):
    with pytest.raises(TypeError):
        Table(
            constants["API_KEY"],
            constants["BASE_ID"],
            constants["TABLE_NAME"],
            request_strategy=invalid_request_strategy,
        )
