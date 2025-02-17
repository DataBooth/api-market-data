import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from marketstack import MarketstackClient, convert_to_dataframe, create_stock_chart


def main():
    st.set_page_config(layout="wide", page_title="Stock Data App")

    st.title("Stock Data Visualisation Tool")

    client = MarketstackClient()

    # Sidebar Inputs
    with st.sidebar:
        #symbol = st.text_input("Enter Stock Symbol", value="AAPL").upper()
        exchange_mic = st.text_input("Enter Exchange MIC", value="XASX").upper()
        start_date = st.date_input("Start Date", value=datetime.today() - timedelta(days=148), format="DD-MM-YYYY")
        end_date = st.date_input("End Date", value=datetime.today() - timedelta(days=4), format="DD-MM-YYYY")

        # Get list of symbols for chosen exchange
        try:
            exchange_data, _ = client.fetch_exchange_tickers(exchange_mic)
            if exchange_data and 'data' in exchange_data and 'tickers' in exchange_data['data']:
                # Ensure data is a list before iterating
                if isinstance(exchange_data['data']['tickers'], list):
                    symbols_for_exchange = [ticker['symbol'] for ticker in exchange_data['data']['tickers']]
                    selected_symbol_exchange = st.selectbox(f"Select symbol from {exchange_mic}", options=symbols_for_exchange)
                else:
                    st.warning(f"Unexpected data format for exchange tickers from {exchange_mic}")
                    selected_symbol_exchange = None
            else:
                st.warning(f"Could not retrieve tickers for exchange {exchange_mic}")
                selected_symbol_exchange = None
        except Exception as e:
            st.error(f"Error fetching tickers for exchange {exchange_mic}: {e}")
            selected_symbol_exchange = None

    tab1, tab2 = st.tabs(["Market Data", "Cache Info"])

    with tab1:

        # Determine which symbol to use
        display_symbol = selected_symbol_exchange if selected_symbol_exchange else None #symbol
        st.subheader(f"{display_symbol} Stock Data")

        # Fetch stock data
        data, from_cache = client.fetch_stock_data(display_symbol, start_date=start_date, end_date=end_date)  # Pass the selected symbol
        # Check if data is valid before converting to DataFrame
        if data and 'data' in data and data['data']:
            df = convert_to_dataframe(data)
            st.dataframe(df)
            fig = create_stock_chart(data, display_symbol)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"No data available for the symbol {display_symbol}.")
            df = None
            fig = None

        if data:
            with st.expander("Expand to view raw JSON data from API for stock price..."):
                st.json(data)


        try:
            exchange_info, from_cache = client.fetch_exchange_info(exchange_mic)

            if exchange_info and 'data' in exchange_info and exchange_info['data']:
                if "mic" in exchange_info["data"] and "country_code" in exchange_info["data"]:
                    st.subheader(f'Exchange details: {exchange_info["data"]["mic"]} - ({exchange_info["data"]["country_code"].lower()})')

                if "website" in exchange_info["data"]:
                    st.markdown(f"Exchange website: {exchange_info["data"]["website"].lower()}")

                with st.expander("Expand to view raw JSON data from API for exchange..."):
                    st.json(exchange_info)
            else:
                st.warning(f"Could not retrieve information for exchange {exchange_mic}")

        except Exception as e:
            st.error(f"Error fetching information for exchange {exchange_mic}: {e}")

        col_left, _ = st.columns([1, 2])
        with col_left:
            st.info(f"Data source: {'Cache' if from_cache else 'Live API'}")

    with tab2:
        st.subheader("Marketstack API - Cache Analysis")

        # Display cache statistics
        try:
            stats = client.get_cache_stats()
            st.write("Cache Statistics:", stats)
        except Exception as e:
            st.error(f"Error retrieving cache statistics: {e}")

        # Display unique endpoints
        try:
            endpoints = client.get_unique_endpoints()
            selected_endpoint = st.selectbox(
                "Select an endpoint to analyze:", endpoints
            )

            # Display API calls for selected endpoint
            calls = client.get_api_calls_by_endpoint(selected_endpoint)
            st.write(f"API Calls for {selected_endpoint}:", calls)
        except Exception as e:
            st.error(f"Error retrieving endpoint data: {e}")

        # Option to clear cache
        if st.button("Clear Cache"):
            try:
                client.clear_cache()
                st.success("Cache cleared successfully!")
            except Exception as e:
                st.error(f"Error clearing cache: {e}")

        # Option to remove old cache entries
        days = st.number_input(
            "Remove entries older than (days):", min_value=1, value=30
        )
        if st.button("Remove Old Entries"):
            try:
                client.remove_old_cache_entries(days)
                st.success(f"Removed cache entries older than {days} days!")
            except Exception as e:
                st.error(f"Error removing old cache entries: {e}")


if __name__ == "__main__":
    main()
