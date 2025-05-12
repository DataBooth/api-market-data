import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd


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
