import pytest
from unittest.mock import patch, MagicMock
from marketstack import MarketstackClient


@pytest.fixture
def mock_client():
    """Fixture to create a MarketstackClient instance with a mock database."""
    with patch("marketstack.DatabaseManager") as MockDatabaseManager:
        mock_db = MockDatabaseManager.return_value
        client = MarketstackClient()
        client.db = mock_db  # Replace the real DB manager with the mock
        yield client


@patch("httpx.get")
def test_fetch_stock_data(mock_get, mock_client):
    """Test fetching stock data from the API."""
    # Mock API response
    mock_response = {
        "data": [
            {
                "date": "2025-01-01",
                "open": 100,
                "high": 110,
                "low": 90,
                "close": 105,
                "volume": 1000,
            }
        ]
    }
    mock_get.return_value.json.return_value = mock_response
    mock_get.return_value.raise_for_status = MagicMock()

    # Ensure cache miss
    mock_client.db.get_cached_response.return_value = None

    # Call the method
    symbol = "AAPL"
    data, from_cache = mock_client.fetch_stock_data(symbol)

    # Assertions
    assert not from_cache  # Data should come from live API
    assert data == mock_response  # Ensure the response matches the mocked data
    mock_get.assert_called_once_with(
        f"https://api.marketstack.com/v2/eod",
        params={"access_key": mock_client.api_key, "symbols": symbol},
    )
    mock_client.db.log_and_cache_response.assert_called_once()


@patch("httpx.get")
def test_fetch_exchange_tickers(mock_get, mock_client):
    """Test fetching exchange tickers."""
    # Mock API response
    mock_response = {
        "data": {
            "tickers": [
                {"symbol": "AAPL", "name": "Apple Inc."},
                {"symbol": "MSFT", "name": "Microsoft Corp."},
            ]
        }
    }
    mock_get.return_value.json.return_value = mock_response
    mock_get.return_value.raise_for_status = MagicMock()

    # Ensure cache miss
    mock_client.db.get_cached_response.return_value = None

    # Call the method
    mic = "XASX"
    data, from_cache = mock_client.fetch_exchange_tickers(mic)

    # Assertions
    assert not from_cache  # Data should come from live API
    assert data == mock_response  # Ensure the response matches the mocked data
    mock_get.assert_called_once_with(
        f"https://api.marketstack.com/v2/exchanges/{mic}/tickers",
        params={"access_key": mock_client.api_key},
    )
    mock_client.db.log_and_cache_response.assert_called_once()


def test_fetch_stock_data_from_cache(mock_client):
    """Test fetching stock data from the cache."""
    # Mock cached response in the database manager
    cached_response = {
        "data": [
            {
                "date": "2025-01-01",
                "open": 100,
                "high": 110,
                "low": 90,
                "close": 105,
                "volume": 1000,
            }
        ]
    }
    mock_client.db.get_cached_response.return_value = cached_response

    # Call the method
    symbol = "AAPL"
    data, from_cache = mock_client.fetch_stock_data(symbol)

    # Assertions
    assert from_cache  # Data should come from cache
    assert data == cached_response  # Ensure the response matches the cached data
    mock_client.db.get_cached_response.assert_called_once()
    mock_client.db.log_and_cache_response.assert_not_called()
