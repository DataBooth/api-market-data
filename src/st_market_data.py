import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from marketstack import MarketstackClient, convert_to_dataframe, create_stock_chart


def main():
    st.set_page_config(layout="wide", page_title="Stock Data App")
    
    st.title("Stock Data Visualisation Tool")
    
    client = MarketstackClient()

    symbol = st.sidebar.text_input("Enter Stock Symbol", value="AAPL")
    exchange_mic = st.sidebar.text_input("Enter Exchange MIC", value="XASX")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"{symbol} Stock Data")
        data, from_cache = client.fetch_stock_data(symbol)
        df = convert_to_dataframe(data)

        st.dataframe(df)
        
        st.info(f"Data source: {'Cache' if from_cache else 'Live API'}")
        
        with st.expander("View Raw JSON Data"):
            st.json(data)

        fig = create_stock_chart(data, symbol)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(f"{exchange_mic} Exchange Info")
        exchange_info, from_cache = client.fetch_exchange_info(exchange_mic)
        
        st.info(f"Data source: {'Cache' if from_cache else 'Live API'}")
        
        if 'website' in exchange_info["data"]:
            st.metric("Website", exchange_info["data"]['website'])
        if 'mic' in exchange_info:
            st.metric("MIC", exchange_info["data"]['mic'])
        if 'country' in exchange_info:
            st.metric("Country code", exchange_info["data"]['country_code'])
        
        with st.expander("View Raw JSON Data"):
            st.json(exchange_info)

if __name__ == "__main__":
    main()
