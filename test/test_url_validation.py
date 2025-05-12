import pytest
from marketstack import MarketstackClient 

@pytest.fixture
def client():
    return MarketstackClient() # No db path so won't create a db


def test_validate_api_request_valid_eod(client):
    endpoint = "eod"
    params = {"access_key": "test_key", "symbols": "AAPL"}
    url, is_valid, errors = client.validate_api_request(endpoint, params)
    assert is_valid
    assert not errors
    assert "access_key=test_key" in url
    assert "symbols=AAPL" in url

def test_validate_api_request_missing_required_param(client):
    endpoint = "eod"
    params = {"symbols": "AAPL"}  # Missing access_key
    url, is_valid, errors = client.validate_api_request(endpoint, params)
    assert not is_valid
    assert errors
    assert "Missing required parameters: access_key" in errors[0]

def test_validate_api_request_invalid_param(client):
    endpoint = "eod"
    params = {"access_key": "test_key", "symbols": "AAPL", "invalid_param": "value"}
    url, is_valid, errors = client.validate_api_request(endpoint, params)
    assert not is_valid
    assert errors
    assert "Invalid parameters: invalid_param" in errors[0]

def test_validate_api_request_invalid_endpoint(client):
    endpoint = "invalid_endpoint"
    params = {"access_key": "test_key"}
    url, is_valid, errors = client.validate_api_request(endpoint, params)
    assert not is_valid
    assert errors
    assert "No matching endpoint configuration found for: invalid_endpoint" in errors[0]

def test_validate_api_request_eod_with_dates(client):
    endpoint = "eod"
    params = {"access_key": "test_key", "symbols": "AAPL", "date_from": "2024-01-01", "date_to": "2024-01-05"}
    url, is_valid, errors = client.validate_api_request(endpoint, params)
    assert is_valid
    assert not errors
    assert "date_from=2024-01-01" in url
    assert "date_to=2024-01-05" in url

def test_validate_api_request_tickers_symbol(client):
    endpoint = "tickers/AAPL"
    params = {"access_key": "test_key"}
    url, is_valid, errors = client.validate_api_request(endpoint, params)
    assert is_valid
    assert not errors
    assert "tickers/AAPL" in url
    assert "access_key=test_key" in url
