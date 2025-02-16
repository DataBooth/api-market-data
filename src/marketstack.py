import json
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, List

import duckdb
import httpx
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv
from loguru import logger
from plotly.subplots import make_subplots

load_dotenv()


class MarketstackClient:
    def __init__(self, db_path: str = "marketstack_cache.db"):
        self.api_key = os.getenv("MARKETSTACK_API_KEY")
        if not self.api_key:
            raise ValueError("MARKETSTACK_API_KEY not found in environment variables")
        self.base_url = "https://api.marketstack.com/v2"
        self.db = DatabaseManager(db_path)

    def fetch_stock_data(
        self, symbol: str, endpoint: str = "eod"
    ) -> Tuple[Dict[str, Any], bool]:
        params = {"access_key": self.api_key, "symbols": symbol}

        # Check cache first
        cached_response = self.db.get_cached_response(endpoint, params)
        if cached_response:
            return cached_response, True  # True indicates data from cache

        # If not in cache, make API call
        url = f"{self.base_url}/{endpoint}"
        response = httpx.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Log the call and cache the response
        self.db.log_and_cache_response(endpoint, params, data)

        return data, False  # False indicates data from live API

    def fetch_intraday_data(self, symbol: str) -> Tuple[Dict[str, Any], bool]:
        return self._make_request("intraday", {"symbols": symbol})

    def fetch_ticker_info(self, symbol: str) -> Tuple[Dict[str, Any], bool]:
        return self._make_request(f"tickers/{symbol}", {})

    def fetch_exchange_info(self, mic: str) -> Tuple[Dict[str, Any], bool]:
        return self._make_request(f"exchanges/{mic}", {})

    def fetch_exchange_tickers(self, mic: str) -> Tuple[Dict[str, Any], bool]:
        return self._make_request(f"exchanges/{mic}/tickers", {})

    def fetch_latest_data(self, symbol: str) -> Tuple[Dict[str, Any], bool]:
        return self._make_request("eod/latest", {"symbols": symbol})

    def fetch_tickers_list(self) -> Tuple[Dict[str, Any], bool]:
        return self._make_request("tickerslist", {})

    def _make_request(
        self, endpoint: str, params: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], bool]:
        params["access_key"] = self.api_key
        url = f"{self.base_url}/{endpoint}"

        # Check cache first
        cached_response = self.db.get_cached_response(endpoint, params)
        if cached_response:
            return cached_response, True

        # If not in cache, make API call
        try:
            response = httpx.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            # Log the call and cache the response
            self.db.log_and_cache_response(endpoint, params, data)
            return data, False
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            return {"error": str(e)}, False
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return {"error": str(e)}, False
        

    def get_cache_stats(self) -> Dict[str, Any]:
        return self.db.get_cache_stats()

    def get_unique_endpoints(self) -> List[str]:
        return self.db.get_unique_endpoints()

    def get_api_calls_by_endpoint(self, endpoint: str) -> pd.DataFrame:
        return self.db.get_api_calls_by_endpoint(endpoint)

    def clear_cache(self):
        self.db.clear_cache()

    def remove_old_cache_entries(self, days: int):
        self.db.remove_old_cache_entries(days)

class DatabaseManager:
    def __init__(self, db_path: str):
        self.con = duckdb.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        self.con.execute("CREATE SEQUENCE IF NOT EXISTS id_sequence START 1")
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS api_calls (
                id INTEGER PRIMARY KEY DEFAULT nextval('id_sequence'),
                endpoint VARCHAR,
                params JSON,
                timestamp TIMESTAMP,
                response JSON
            )
        """
        )

    def get_cached_response(
        self, endpoint: str, params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        query = """
            SELECT response
            FROM api_calls
            WHERE endpoint = ? AND params = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """
        result = self.con.execute(query, [endpoint, json.dumps(params)]).fetchone()
        return json.loads(result[0]) if result else None

    def log_and_cache_response(
        self, endpoint: str, params: Dict[str, Any], response: Dict[str, Any]
    ):
        query = """
            INSERT INTO api_calls (endpoint, params, timestamp, response)
            VALUES (?, ?, ?, ?)
        """
        self.con.execute(
            query, [endpoint, json.dumps(params), datetime.now(), json.dumps(response)]
        )


    def get_all_api_calls(self) -> pd.DataFrame:
        """Retrieve all API calls from the cache."""
        query = "SELECT * FROM api_calls ORDER BY timestamp DESC"
        return self.con.execute(query).df()

    def get_api_calls_by_endpoint(self, endpoint: str) -> pd.DataFrame:
        """Retrieve API calls for a specific endpoint."""
        query = "SELECT * FROM api_calls WHERE endpoint = ? ORDER BY timestamp DESC"
        return self.con.execute(query, [endpoint]).df()

    def get_latest_api_call(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve the latest API call for a specific endpoint and parameters."""
        query = """
            SELECT *
            FROM api_calls
            WHERE endpoint = ? AND params = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """
        result = self.con.execute(query, [endpoint, json.dumps(params)]).fetchone()
        return dict(result) if result else None

    def get_unique_endpoints(self) -> List[str]:
        """Get a list of unique endpoints in the cache."""
        query = "SELECT DISTINCT endpoint FROM api_calls"
        return [row[0] for row in self.con.execute(query).fetchall()]

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        query = """
            SELECT 
                COUNT(*) as total_calls,
                COUNT(DISTINCT endpoint) as unique_endpoints,
                MIN(timestamp) as oldest_call,
                MAX(timestamp) as newest_call
            FROM api_calls
        """
        result = self.con.execute(query).fetchone()
        if result:
            return {
                "total_calls": result[0],
                "unique_endpoints": result[1],
                "oldest_call": result[2],
                "newest_call": result[3],
            }
        else:
            return {}

    def clear_cache(self):
        """Clear all data from the cache."""
        self.con.execute("DELETE FROM api_calls")

    def remove_old_cache_entries(self, days: int):
        """Remove cache entries older than specified number of days."""
        query = "DELETE FROM api_calls WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL ? DAY"
        self.con.execute(query, [days])


def create_stock_chart(data: Dict[str, Any], symbol: str):
    # Convert the data to a pandas DataFrame
    df = pd.DataFrame(data["data"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Create the figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add candlestick trace
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
        )
    )

    # Add volume bar chart
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["volume"],
            name="Volume",
            marker_color="rgba(0, 0, 255, 0.3)",
        ),
        secondary_y=True,
    )

    # Update layout
    fig.update_layout(
        title=f"{symbol} Stock Price and Volume",
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        yaxis2_title="Volume",
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # Update y-axes
    fig.update_yaxes(title_text="Price (USD)", secondary_y=False)
    fig.update_yaxes(title_text="Volume", secondary_y=True)

    return fig


def convert_to_dataframe(data: Dict[str, Any]) -> pd.DataFrame:
    if "data" in data and isinstance(data["data"], list):
        df = pd.DataFrame(data["data"])
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date")
    else:
        raise ValueError("Unexpected data format in API response")


def main():
    client = MarketstackClient()

    symbol = "AAPL"

    data, from_cache = client.fetch_stock_data(symbol)
    df = convert_to_dataframe(data)

    print(df.head())

    logger.info(f"Apple Stock Data (from {'cache' if from_cache else 'live API'}):")
    print(json.dumps(data, indent=2))

    # Create and show the chart
    fig = create_stock_chart(data, symbol)
    fig.show()

    exchange_mic = "XASX"
    exchange_info, from_cache = client.fetch_exchange_info(exchange_mic)

    print(
        f"\n{exchange_mic} Exchange Info (from {'cache' if from_cache else 'live API'}):"
    )
    print(json.dumps(exchange_info, indent=2))


if __name__ == "__main__":
    main()
