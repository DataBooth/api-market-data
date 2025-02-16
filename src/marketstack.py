import json
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import duckdb
import httpx
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv
from loguru import logger
from plotly.subplots import make_subplots

load_dotenv()

class MarketstackClient:
    def __init__(self, db_path: str = 'marketstack_cache.db'):
        self.api_key = os.getenv('MARKETSTACK_API_KEY')
        if not self.api_key:
            raise ValueError("MARKETSTACK_API_KEY not found in environment variables")
        self.base_url = "https://api.marketstack.com/v2"
        self.db = DatabaseManager(db_path)

    def fetch_stock_data(self, symbol: str, endpoint: str = "eod") -> Tuple[Dict[str, Any], bool]:
        params = {
            "access_key": self.api_key,
            "symbols": symbol
        }

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

class DatabaseManager:
    def __init__(self, db_path: str):
        self.con = duckdb.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        self.con.execute("CREATE SEQUENCE IF NOT EXISTS id_sequence START 1")
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS api_calls (
                id INTEGER PRIMARY KEY DEFAULT nextval('id_sequence'),
                endpoint VARCHAR,
                params JSON,
                timestamp TIMESTAMP,
                response JSON
            )
        """)

    def get_cached_response(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        query = """
            SELECT response
            FROM api_calls
            WHERE endpoint = ? AND params = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """
        result = self.con.execute(query, [endpoint, json.dumps(params)]).fetchone()
        return json.loads(result[0]) if result else None

    def log_and_cache_response(self, endpoint: str, params: Dict[str, Any], response: Dict[str, Any]):
        query = """
            INSERT INTO api_calls (endpoint, params, timestamp, response)
            VALUES (?, ?, ?, ?)
        """
        self.con.execute(query, [endpoint, json.dumps(params), datetime.now(), json.dumps(response)])


def create_stock_chart(data: Dict[str, Any], symbol: str):
    # Convert the data to a pandas DataFrame
    df = pd.DataFrame(data['data'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Create the figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add candlestick trace
    fig.add_trace(
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="Price"
        )
    )

    # Add volume bar chart
    fig.add_trace(
        go.Bar(
            x=df['date'],
            y=df['volume'],
            name="Volume",
            marker_color='rgba(0, 0, 255, 0.3)'
        ),
        secondary_y=True
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
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Update y-axes
    fig.update_yaxes(title_text="Price (USD)", secondary_y=False)
    fig.update_yaxes(title_text="Volume", secondary_y=True)

    return fig

def main():
    client = MarketstackClient()
    

    symbol = "AAPL"

    apple_data, from_cache = client.fetch_stock_data(symbol)
    logger.info(f"Apple Stock Data (from {'cache' if from_cache else 'live API'}):")
    #print(json.dumps(apple_data, indent=2))

    # Create and show the chart
    fig = create_stock_chart(apple_data, symbol)
    fig.show()


if __name__ == "__main__":
    main()
