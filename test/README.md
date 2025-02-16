# MarketstackClient Test Suite

This test suite covers the core functionality of the `MarketstackClient` class, which interacts with the Marketstack API and manages data caching.

## Test Cases

### 1. test_fetch_stock_data
Tests the retrieval of stock data from the API when the data is not in the cache.

### 2. test_fetch_exchange_tickers
Verifies the fetching of exchange tickers from the API.

### 3. test_fetch_stock_data_from_cache
Ensures that cached stock data is correctly retrieved without making an API call.

## Why Simulate Database and API Calls?

In unit testing, we simulate (mock) database and API calls for several important reasons:

1. **Isolation**: By mocking external dependencies, we ensure that we're testing only the `MarketstackClient` logic, not the behaviour of the database or the Marketstack API.

2. **Consistency**: API responses can vary, and databases can be in different states. Mocking ensures our tests always run with the same data.

3. **Speed**: Real API calls and database operations are slow. Mocks make our tests run much faster.

4. **Reliability**: Tests don't fail due to network issues, API downtime, or database connection problems.

5. **Control**: We can easily simulate various scenarios (e.g., API errors, cache hits/misses) that might be difficult to reproduce with real systems.

6. **Cost**: Many APIs have usage limits or costs associated with calls. Mocking prevents unnecessary API usage during testing.

## How Simulation Works

- **Database Simulation**: We use a mock `DatabaseManager` to simulate cache operations without interacting with a real database.
- **API Simulation**: The `httpx.get` method is patched to return predefined responses, simulating API calls without actually contacting the Marketstack server.

This approach allows us to comprehensively test the client's behaviour in various scenarios while maintaining fast, reliable, and isolated tests.
