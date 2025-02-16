from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import tomllib

from marketstack import MarketstackClient


def populate_test_database():
    with open(Path.cwd() / "test_data.toml", "rb") as f:
        params = tomllib.load(f)

    symbols = params["test_parameters"]["symbols"]
    end_date = datetime.fromisoformat(params["test_parameters"]["end_date"])
    start_date = end_date - timedelta(days=params["test_parameters"]["days_range"])
    api_version = params["test_parameters"]["api_version"]
    database_file = params["test_parameters"]["database_file"]

    client = MarketstackClient()
    conn = duckdb.connect(Path.cwd() / "data" / database_file)

    # Create the stock_data table if it doesn't exist
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_data (
            symbol VARCHAR,
            date DATE,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT
        )
    """
    )

    # Create the test_metadata table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS test_metadata (
            key VARCHAR PRIMARY KEY,
            value VARCHAR
        )
    """
    )

    for symbol in symbols:
        data, _ = client.fetch_stock_data(
            symbol, start_date=start_date, end_date=end_date
        )
        if "data" in data:
            for item in data["data"]:
                conn.execute(
                    """
                    INSERT INTO stock_data VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        symbol,
                        item["date"],
                        item["open"],
                        item["high"],
                        item["low"],
                        item["close"],
                        item["volume"],
                    ),
                )

    # Insert metadata
    generation_time = datetime.now().isoformat()
    conn.execute(
        """
        INSERT OR REPLACE INTO test_metadata VALUES 
        ('generation_time', ?),
        ('start_date', ?),
        ('end_date', ?),
        ('symbols', ?),
        ('api_version', ?)
    """,
        (
            generation_time,
            start_date.isoformat(),
            end_date.isoformat(),
            ",".join(symbols),
            api_version,
        ),
    )

    conn.close()
    print(f"Test database populated with real Marketstack data at {generation_time}.")


if __name__ == "__main__":
    populate_test_database()
