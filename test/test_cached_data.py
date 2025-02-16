from datetime import datetime, timedelta

import duckdb
import pytest

from marketstack import MarketstackClient, convert_to_dataframe

# Constants
TEST_DB_PATH = 'data/test_marketstack_17Feb2025.db'
TEST_SYMBOL = 'AAPL'
TEST_EXCHANGE = 'XNAS'
TEST_DATE = datetime(2025, 2, 5)  # Assuming we have data for this date

@pytest.fixture(scope="module")
def test_client():
    """Create a MarketstackClient instance using the test database."""
    return MarketstackClient(db_path=TEST_DB_PATH)

@pytest.fixture(scope="module")
def db_connection():
    """Create a connection to the test database."""
    return duckdb.connect(TEST_DB_PATH)

def test_fetch_stock_data_real(test_client, db_connection):
    """Test fetching stock data using real data from the test database."""
    data, from_cache = test_client.fetch_stock_data(TEST_SYMBOL, start_date=TEST_DATE, end_date=TEST_DATE + timedelta(days=7))
    
    # Verify data structure
    assert 'data' in data
    assert isinstance(data['data'], list)
    assert len(data['data']) > 0
    
    # Verify specific data points
    first_entry = data['data'][0]
    assert 'date' in first_entry
    assert 'open' in first_entry
    assert 'close' in first_entry
    
    # Verify against database
    db_data = db_connection.execute(f"""
        SELECT * FROM stock_data 
        WHERE symbol = '{TEST_SYMBOL}' 
        AND date BETWEEN '{TEST_DATE}' AND '{TEST_DATE + timedelta(days=7)}'
        ORDER BY date
    """).fetchall()
    
    assert len(data['data']) == len(db_data)
    assert data['data'][0]['date'] == db_data[0][1].strftime('%Y-%m-%d')
    assert data['data'][0]['close'] == db_data[0][5]

def test_fetch_exchange_tickers_real(test_client, db_connection):
    """Test fetching exchange tickers using real data from the test database."""
    data, from_cache = test_client.fetch_exchange_tickers(TEST_EXCHANGE)
    
    # Verify data structure
    assert 'data' in data
    assert 'tickers' in data['data']
    assert isinstance(data['data']['tickers'], list)
    assert len(data['data']['tickers']) > 0
    
    # Verify specific data points
    first_ticker = data['data']['tickers'][0]
    assert 'symbol' in first_ticker
    assert 'name' in first_ticker
    
    # Verify against database
    db_tickers = db_connection.execute(f"""
        SELECT DISTINCT symbol, name FROM exchange_tickers 
        WHERE exchange = '{TEST_EXCHANGE}'
        ORDER BY symbol
    """).fetchall()
    
    assert len(data['data']['tickers']) == len(db_tickers)
    assert data['data']['tickers'][0]['symbol'] == db_tickers[0][0]
    assert data['data']['tickers'][0]['name'] == db_tickers[0][1]

def test_caching_behavior_real(test_client):
    """Test the caching behavior using real data."""
    # First call should not be from cache
    data1, from_cache1 = test_client.fetch_stock_data(TEST_SYMBOL, start_date=TEST_DATE, end_date=TEST_DATE)
    assert not from_cache1
    
    # Second call with same parameters should be from cache
    data2, from_cache2 = test_client.fetch_stock_data(TEST_SYMBOL, start_date=TEST_DATE, end_date=TEST_DATE)
    assert from_cache2
    assert data1 == data2

def test_convert_to_dataframe_real(test_client):
    """Test converting real API response to DataFrame."""
    data, _ = test_client.fetch_stock_data(TEST_SYMBOL, start_date=TEST_DATE, end_date=TEST_DATE + timedelta(days=7))
    df = convert_to_dataframe(data)
    
    assert not df.empty
    assert 'date' in df.columns
    assert 'open' in df.columns
    assert 'close' in df.columns
    assert df['date'].dtype == 'datetime64[ns]'
    assert df['open'].dtype == 'float64'
    assert df['close'].dtype == 'float64'

