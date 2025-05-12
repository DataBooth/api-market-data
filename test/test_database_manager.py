import pytest
from database_manager import DatabaseManager
from datetime import datetime, timedelta


@pytest.fixture
def db_manager():
    """Fixture to create a DatabaseManager instance."""
    return DatabaseManager(":memory:")  # Use an in-memory DuckDB database for testing


def test_log_and_cache_response(db_manager):
    """Test logging and caching an API response."""
    endpoint = "/eod"
    params = {"symbols": "AAPL"}
    response = {"data": [{"date": "2025-01-01", "close": 105}]}

    db_manager.log_and_cache_response(endpoint, params, response)

    # Query the database to verify insertion
    result = db_manager.con.execute("SELECT * FROM api_calls").fetchall()

    assert len(result) == 1  # Ensure one row was inserted
    assert result[0][1] == endpoint  # Check endpoint column matches


def test_get_cached_response(db_manager):
    """Test retrieving a cached response."""
    endpoint = "/eod"
    params = {"symbols": "AAPL"}
    response = {"data": [{"date": "2025-01-01", "close": 105}]}

    db_manager.log_and_cache_response(endpoint, params, response)

    cached_response = db_manager.get_cached_response(endpoint, params)

    assert cached_response == response  # Ensure retrieved response matches


def test_clear_cache(db_manager):
    """Test clearing all cache entries."""
    endpoint = "/eod"
    params = {"symbols": "AAPL"}

    db_manager.log_and_cache_response(endpoint, params, {"data": []})

    db_manager.clear_cache()

    result = db_manager.con.execute("SELECT * FROM api_calls").fetchall()

    assert len(result) == 0  # Ensure all rows were deleted


def test_remove_old_cache_entries(db_manager):
    """Test removing old cache entries."""


# Insert two entries: one recent and one old.
recent_time = datetime.now()
old_time = datetime.now() - timedelta(days=30)
