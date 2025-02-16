# `api-market-data`

## Overview

This project provides a Python-based solution for integrating with the [Marketstack](https://www.marketstack.com) API to retrieve stock market data. It incorporates a caching mechanism using [DuckDB](https://duckdb.org) to minimise API calls and improve performance. 

The code is structured around two core classes: `MarketstackClient` and `DatabaseManager`. A [Streamlit](https://streamlit.io) application provides a user-friendly interface to explore the retrieved data.

## What

The project consists of:

*   **`MarketstackClient`:** A class responsible for interacting with the Marketstack API, fetching data for various endpoints (End-of-Day, Intraday, Ticker Information, etc.). It also handles caching of API responses.
*   **`DatabaseManager`:** A class that manages a DuckDB database for caching API responses. It provides methods for storing, retrieving, and managing cached data.
*   **Utility Functions:** Helper functions for data conversion (e.g., converting API responses to Pandas dataframes) and visualisation (creating stock charts).
*   **Streamlit Application:** A Streamlit app to visualise and interact with the data retrieved by the `MarketstackClient`. *(Further refinement is planned)*.

## Why

The primary goals of this project are:

*   **Efficient Data Retrieval:** To streamline the process of fetching stock market data from the Marketstack API.
*   **Reduced API Usage:** To minimise the number of API calls by caching frequently accessed data. The Marketstack API has rate limits, so this is crucial for sustainable use.
*   **Improved Performance:** To provide faster access to data by retrieving it from the cache when available.
*   **Data Exploration:** To offer a user-friendly way to explore and visualise the retrieved data.
*   **Flexibility and Extensibility:**  To provide a modular design that can be easily extended to support additional Marketstack API endpoints and data analysis techniques.

## How

### Core Components

1.  **API Key Management:** The `MarketstackClient` securely loads the Marketstack API key from an environment variable (`MARKETSTACK_API_KEY`) using the `python-dotenv` library.

2.  **Data Fetching:** The `MarketstackClient` provides methods for fetching data from various Marketstack API endpoints (e.g., `fetch_stock_data`, `fetch_intraday_data`, `fetch_ticker_info`). These methods construct API requests, handle responses, and manage caching. The `_make_request` method centralises the API calling logic.

3.  **Caching Mechanism:**
    *   The `DatabaseManager` uses DuckDB, an in-process analytical database, to store API responses.
    *   API calls are cached in the `api_calls` table.
    *   Before making an API call, the `MarketstackClient` checks the cache for a matching response. If found, the cached data is returned.
    *   API responses are stored in the cache along with the request parameters and timestamp.

4.  **Data Conversion:**
    *   The `convert_to_dataframe` function converts API responses to Pandas DataFrames for easier manipulation and analysis.
    *   The `create_stock_chart` function uses Plotly to create interactive stock charts from the data.

### Streamlit Application (In progress)

The Streamlit application is intended to provide a user-friendly interface for:

*   **Selecting Stock Symbols:** Allowing users to specify the stock symbol to retrieve data for.
*   **Choosing API Endpoints:** Providing options to select different Marketstack API endpoints (e.g., End-of-Day data, Intraday data, Ticker Information).
*   **Visualising Data:** Displaying the retrieved data in tabular format (using Streamlit's `st.dataframe`) and as interactive charts (using Plotly).
*   **Cache Management:** Providing tools to view cache statistics, clear the cache, and remove old cache entries.
*   **Secure Key Handling:** The key is obtained via the `python-dotenv` package and is not exposed to the front end.

### Code Structure

*   **`marketstack.py`:** Contains the `MarketstackClient`, `DatabaseManager`, `convert_to_dataframe`, and `create_stock_chart` functions.
*   **`st_market_data.py`:** (*in progress*) Contains the Streamlit application logic (UI elements, data fetching, and display).

## Marketstack API Endpoints

The `MarketstackClient` currently supports the following [Marketstack API endpoints](https://marketstack.com/documentation_v2):

*   **End-of-Day Data (`/eod`):** Retrieves end-of-day data for a specified stock symbol.  Provides open, high, low, close, and volume information for a given date. Accessed via `fetch_stock_data`.
*   **Intraday Data (`/intraday`):** Retrieves intraday data for a specified stock symbol.  Provides price and volume information at smaller intervals within a trading day. Accessed via `fetch_intraday_data`.
*   **Ticker Information (`/tickers/{symbol}`):** Retrieves general information about a specific stock ticker symbol (e.g., company name, exchange, sector). Accessed via `fetch_ticker_info`.
*   **Exchange Information (`/exchanges/{mic}`):** Retrieves information about a specific stock exchange, identified by its Market Identifier Code (MIC). Accessed via `fetch_exchange_info`.
*   **Exchange Tickers (`/exchanges/{mic}/tickers`):** Retrieves a list of tickers traded on a specific stock exchange. Accessed via `fetch_exchange_tickers`.
*   **Latest End-of-Day Data (`/eod/latest`):** Retrieves the most recent end-of-day data for a given stock symbol. Accessed via `fetch_latest_data`.
*   **Tickers List (`/tickers`):** Retrieves a list of all supported tickers.  Provides a comprehensive catalog of available symbols. Accessed via `fetch_tickers_list`.


### How to Run

1.  **Install Dependencies:**
   
    - Production  
    `uv add httpx duckdb pandas plotly python-dotenv loguru streamlit watchdog`

    - Development  
    `uv add --dev pytest black`

2.  **Set up Environment Variables:**
    *   Create a `.env` file in the project directory.
    *   Add your Marketstack API key to the `.env` file:

        ```
        MARKETSTACK_API_KEY=YOUR_MARKETSTACK_API_KEY
        ```

    *   **Important:**  Note that the `.env` file is added to `.gitignore` to exclude from the repository.

3.  **Streamlit app:** Run the Streamlit application:

    ```
    streamlit run src/st_market_data.py
    ```

### Testing

See [test/README.md](test/README.md).

### Future Enhancements

*   **More Streamlit Features:** Implement all the planned Streamlit functionalities (cache management, endpoint selection, etc.).
*   **Asynchronous API Calls:** Convert the API calls to asynchronous operations using `asyncio` and `httpx` for improved performance.
*   **Cache Expiration:** Implement a mechanism to automatically expire old cache entries.
*   **Error Handling:** Add more robust error handling and logging.
*   **Data Analysis Tools:** Integrate more advanced data analysis techniques (e.g., moving averages, technical indicators).
*   **Unit Tests:** Add unit tests to improve code quality and reliability.
*   **Comprehensive Documentation:** Expand the documentation to cover all aspects of the project in detail.

### Disclaimer

This project is intended for educational and informational purposes only.  It is not financial advice.  Use at your own risk.  Always consult with a qualified financial advisor before making any investment decisions.


## Appendix: Caching Alternatives

### Caching Mechanism:  DuckDB vs. Other Options

While options like Redis or Memcached are commonly used for caching, and simple file-based caches are possible, DuckDB offers a compelling alternative in this context.

*   **File-Based Caching (e.g., JSON or Pickle files):**  A basic approach involves saving API responses directly to files (e.g., as JSON or pickled Python objects). This is simple to implement, but it lacks efficient querying and analysis capabilities, requires manual cache invalidation, and can become slow with large datasets.

*   **Shelve:** The `shelve` module provides a dictionary-like interface backed by disk files. While offering persistence, it's generally slower than in-memory caches and less suitable for complex queries.

*   **Redis/Memcached:**  These in-memory data stores offer very fast caching but introduce an external dependency.  They are ideal for high-performance caching in distributed systems but are overkill for a single-application scenario.

*   **DuckDB:** Offers a compelling alternative due to its zero-dependency, in-process nature, and ability to perform SQL-based analytical queries directly on the cached data. This makes it particularly well-suited for scenarios where you need both efficient caching and data analysis without the overhead of a separate caching server.  It provides the persistence of file-based caches with the query capabilities of a database.

DuckDB provides a balance between simplicity, performance, and analytical capabilities, making it a suitable (though not unique) choice for this application.
