import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import httpx
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv
from loguru import logger
from plotly.subplots import make_subplots
import tomllib
import re
from urllib.parse import urlparse, urlencode, quote
from database_manager import DatabaseManager
from  pathlib import Path

load_dotenv()


class MarketstackClient:
    def __init__(self, db_path: str = "marketstack_cache.db"):
        self.api_key = os.getenv("MARKETSTACK_API_KEY")
        if not self.api_key:
            raise ValueError("MARKETSTACK_API_KEY not found in environment variables")
        self.base_url = "https://api.marketstack.com/v2"
        self.db = DatabaseManager(db_path)
        self.toml_config = self._load_toml_config(Path.cwd() / "src" / "marketstack_api.toml")  # Load TOML config in init

    def _load_toml_config(self, toml_file: str) -> Dict[str, Any]:
        """Loads the TOML configuration file."""
        try:
            with open(toml_file, "rb") as f:
                return tomllib.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"TOML configuration file not found: {toml_file}")
        except Exception as e:
            raise ValueError(f"Error loading TOML configuration: {e}")

    def validate_api_request(self, endpoint: str, params: Dict[str, Any]) -> Tuple[str, bool, List[str]]:
        """
        Validates the API request based on the TOML configuration.

        Args:
            endpoint: The endpoint name (e.g., "eod").
            params: A dictionary of parameters for the request.

        Returns:
            A tuple containing:
            - The validated URL (if valid).
            - A boolean indicating validity (True if valid, False otherwise).
            - A list of validation error messages.
        """
        try:
            endpoint_config = None
            for section, data in self.toml_config.items():
                # Generate the regular expression pattern from the URL
                url_pattern = data["url"].replace("{symbol}", "[^/]+")  # Match any non-slash character
                url_pattern = url_pattern.replace("{mic}", "[^/]+")  # Match any non-slash character
                url_pattern = "^" + url_pattern.replace("/", "\\/") + "$"  # Escape forward slashes and add anchors

                if re.match(url_pattern, endpoint):
                    endpoint_config = data
                    break

            if not endpoint_config:
                return "", False, [f"No matching endpoint configuration found for: {endpoint}"]

            required_params = endpoint_config["required_params"]
            optional_params = endpoint_config["optional_params"]
            base_url = endpoint_config["url"]
            method = endpoint_config["method"]

            errors = []

            # Check for missing required parameters
            missing_params = [param for param in required_params if param not in params]
            if missing_params:
                errors.append(f"Missing required parameters: {', '.join(missing_params)}")

            # Check for invalid parameters
            invalid_params = [
                param for param in params if param not in required_params and param not in optional_params
            ]
            if invalid_params:
                errors.append(f"Invalid parameters: {', '.join(invalid_params)}")

            if errors:
                return "", False, errors

            # Construct the URL
            url = base_url
            # Extract dynamic parts from the endpoint and inject into the URL
            dynamic_parts = re.findall(r"\{([^}]+)\}", url)  # Find all occurrences of {var} in URL
            for part in dynamic_parts:
                if part in endpoint:  #Check if the dynamic part is actually available in the provided endpoint
                    url = url.replace("{" + part + "}", quote(endpoint.split("/")[1]))  # Quote the dynamic part
                else:
                    return "", False, [f"Dynamic part '{part}' not found in endpoint"]


            #Add query parameters
            query_params = {k: v for k, v in params.items() if v is not None}
            url = f"{url}?{urlencode(query_params, quote_via=quote)}"  # Quote the query parameters


            return url, True, []

        except FileNotFoundError:
            return "", False, ["marketstack_api.toml not found"]
        except Exception as e:
            return "", False, [f"An error occurred during validation: {e}"]

    def fetch_stock_data(
        self, 
        symbol: str, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        endpoint: str = "eod"
    ) -> Tuple[Dict[str, Any], bool]:
        params = {"access_key": self.api_key, "symbols": symbol}
        
        if start_date:
            params["date_from"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["date_to"] = end_date.strftime("%Y-%m-%d")

        return self._make_request(endpoint, params)

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

        validated_url, is_valid, errors = self.validate_api_request(endpoint, params)

        if not is_valid:
            logger.error(f"API request validation failed for endpoint {endpoint}: {', '.join(errors)}")
            return {"error": "Invalid API request", "details": errors}, False

        # Check cache first
        cached_response = self.db.get_cached_response(endpoint, params)
        if cached_response:
            return cached_response, True

        # If not in cache, make API call
        try:
            response = httpx.get(validated_url)  # Use the validated URL
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
        
        # Convert date to datetime, handling potential errors
        df["date"] = pd.to_datetime(df["date"], errors='coerce')
        
        # Select numeric columns and the date column
        numeric_cols = df.select_dtypes(include=['number']).columns
        columns_to_keep = list(numeric_cols) + ['date']
        df = df[columns_to_keep]
        
        # Sort by date and reset index
        df = df.sort_values("date", ascending=False).reset_index(drop=True)
        
        return df
    else:
        raise ValueError("Unexpected data format in API response")


def validate_api_request(endpoint: str, params: Dict[str, Any]) -> Tuple[str, bool, List[str]]:
    """
    Validates the API request based on the TOML configuration.

    Args:
        endpoint: The endpoint name (e.g., "eod").
        params: A dictionary of parameters for the request.

    Returns:
        A tuple containing:
        - The validated URL (if valid).
        - A boolean indicating validity (True if valid, False otherwise).
        - A list of validation error messages.
    """
    try:
        with open("marketstack_api.toml", "rb") as f:
            config = tomllib.load(f)

        endpoint_config = None
        for section, data in config.items():
            # Generate the regular expression pattern from the URL
            url_pattern = data["url"].replace("{symbol}", "[^/]+")  # Match any non-slash character
            url_pattern = url_pattern.replace("{mic}", "[^/]+")  # Match any non-slash character
            url_pattern = "^" + url_pattern.replace("/", "\\/") + "$"  # Escape forward slashes and add anchors

            if re.match(url_pattern, endpoint):
                endpoint_config = data
                break

        if not endpoint_config:
            return "", False, [f"No matching endpoint configuration found for: {endpoint}"]

        required_params = endpoint_config["required_params"]
        optional_params = endpoint_config["optional_params"]
        base_url = endpoint_config["url"]
        method = endpoint_config["method"]

        errors = []

        # Check for missing required parameters
        missing_params = [param for param in required_params if param not in params]
        if missing_params:
            errors.append(f"Missing required parameters: {', '.join(missing_params)}")

        # Check for invalid parameters
        invalid_params = [
            param for param in params if param not in required_params and param not in optional_params
        ]
        if invalid_params:
            errors.append(f"Invalid parameters: {', '.join(invalid_params)}")

        if errors:
            return "", False, errors

        # Construct the URL
        url = base_url
        # Extract dynamic parts from the endpoint and inject into the URL
        dynamic_parts = re.findall(r"\{([^}]+)\}", url)  # Find all occurrences of {var} in URL
        for part in dynamic_parts:
            if part in endpoint:  #Check if the dynamic part is actually available in the provided endpoint
                url = url.replace("{" + part + "}", quote(endpoint.split("/")[1]))  # Quote the dynamic part
            else:
                return "", False, [f"Dynamic part '{part}' not found in endpoint"]


        #Add query parameters
        query_params = {k: v for k, v in params.items() if v is not None}
        url = f"{url}?{urlencode(query_params, quote_via=quote)}"  # Quote the query parameters


        return url, True, []

    except FileNotFoundError:
        return "", False, ["marketstack_api.toml not found"]
    except Exception as e:
        return "", False, [f"An error occurred during validation: {e}"]


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
