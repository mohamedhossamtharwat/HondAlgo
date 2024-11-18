import streamlit as st
import pandas as pd
import requests
import time

# ================== FUNCTIONS ==================

def fetch_stock_data(symbol, period):
    # Define the base URL for EODHD API
    base_url = "https://eodhistoricaldata.com/api/eod"

    # Define the period mappings for EODHD
    period_map = {
        "1d": "1d", "5d": "5d", "1 month": "1mo", "3 months": "3mo",
        "6 months": "6mo", "1 year": "1y", "2 years": "2y",
        "5 years": "5y", "10 years": "10y", "max": "max"
    }

    # Map the selected period to EODHD's period
    api_period = period_map.get(period, "1y")

    # Construct the request URL
    url = f"{base_url}/{symbol}.US"

    # Parameters for the API
    params = {
        "api_token": "673b9626ee95c0.80706722",  # Replace with your API key
        "fmt": "json"  # Fetch data in JSON format
    }

    try:
        # Send the API request
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise HTTP errors, if any

        # Parse the JSON data
        data = response.json()

        # Convert JSON to Pandas DataFrame
        df = pd.DataFrame(data)
        df['Date'] = pd.to_datetime(df['date'])
        df.set_index('Date', inplace=True)

        # Ensure required columns exist
        df.rename(columns={"close": "Close", "high": "High", "low": "Low"}, inplace=True)

        return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None


def calculate_indicators(df, ema_fast, ema_mid, ema_slow, wr_length):
    df['EMA_Fast'] = df['Close'].ewm(span=ema_fast, adjust=False).mean()
    df['EMA_Mid'] = df['Close'].ewm(span=ema_mid, adjust=False).mean()
    df['EMA_Slow'] = df['Close'].ewm(span=ema_slow, adjust=False).mean()

    high_roll = df['High'].rolling(window=wr_length)
    low_roll = df['Low'].rolling(window=wr_length)
    df['%R'] = (high_roll.max() - df['Close']) / (high_roll.max() - low_roll.min()) * -100

    df['EMA_Aligned'] = (df['EMA_Fast'] > df['EMA_Mid']) & (df['EMA_Mid'] > df['EMA_Slow'])
    df['WR_Cross'] = (df['%R'].shift(1) <= -80) & (df['%R'] > -80)
    df['Buy_Signal'] = df['EMA_Aligned'] & df['WR_Cross']
    
    return df


# ================== STREAMLIT UI ==================

st.markdown(
    """
    <div style="text-align: center;">
        <h1>HondAlgo</h1>
        <p>Algorithm analyze stock data and detect stocks with high bullish potential.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Sidebar for parameter inputs
st.sidebar.header("Set Parameters")

# Initialize session state variables if not set
if "ema_fast" not in st.session_state:
    st.session_state.ema_fast = 20
if "ema_mid" not in st.session_state:
    st.session_state.ema_mid = 50
if "ema_slow" not in st.session_state:
    st.session_state.ema_slow = 100
if "wr_length" not in st.session_state:
    st.session_state.wr_length = 14
if "period" not in st.session_state:
    st.session_state.period = "1 year"

ema_fast = st.sidebar.number_input("Fast EMA Length", value=st.session_state.ema_fast, min_value=1, key="ema_fast")
ema_mid = st.sidebar.number_input("Mid EMA Length", value=st.session_state.ema_mid, min_value=1, key="ema_mid")
ema_slow = st.sidebar.number_input("Slow EMA Length", value=st.session_state.ema_slow, min_value=1, key="ema_slow")
wr_length = st.sidebar.number_input("Williams %R Length", value=st.session_state.wr_length, min_value=1, key="wr_length")

period = st.sidebar.selectbox(
    "Select Stock Data Period",
    options=["1d", "5d", "1 month", "3 months", "6 months", "1 year", "2 years", "5 years", "10 years", "max"],
    index=["1d", "5d", "1 month", "3 months", "6 months", "1 year", "2 years", "5 years", "10 years", "max"].index(st.session_state.period),
    key="period"
)

reset = st.sidebar.button("Reset Parameters")
if reset:
    st.session_state.ema_fast = 20
    st.session_state.ema_mid = 50
    st.session_state.ema_slow = 100
    st.session_state.wr_length = 14
    st.session_state.period = "1 year"

st.markdown(
    """
    <div style="text-align: center;">
        <h3>Stock Symbols</h3>
        <p>Enter stock symbols (comma-separated)</p>
    </div>
    """,
    unsafe_allow_html=True
)
symbols = st.text_area("", "AAPL, MSFT, TSLA")

# Centered Analyze button
analyze_placeholder = st.markdown(
    """
    <style>
        div.stButton > button {
            display: block;
            margin: 0 auto;
            background-color: #333333;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            border-radius: 5px;
            cursor: pointer;
        }
        div.stButton > button:hover {
            background-color: #444444;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ================== ANALYSIS PROCESS ==================

if st.button("Analyze"):
    stock_symbols = [s.strip() for s in symbols.split(",") if s.strip()]
    
    if not stock_symbols:
        st.error("Please provide at least one stock symbol.")
    else:
        analyzing_placeholder = st.markdown(
            f"<div style='text-align: center; font-size: 18px;'>Analyzing {len(stock_symbols)} stocks 📈💹...</div>",
            unsafe_allow_html=True
        )

        qualifying_stocks = []
        not_qualified_stocks = []
        error_stocks = []
        progress = st.progress(0)
        status_placeholder = st.empty()
        step = 100 / len(stock_symbols)
        stock_icons = ["📈", "📉", "💹", "📊", "💵"]

        for i, symbol in enumerate(stock_symbols):
            current_icon = stock_icons[i % len(stock_icons)]
            status_placeholder.markdown(
                f"<div style='text-align: center; font-size: 18px;'>Analyzing {i+1}/{len(stock_symbols)}: {symbol} {current_icon}</div>",
                unsafe_allow_html=True
            )
            progress.progress(int((i + 1) * step))
            df = fetch_stock_data(symbol, period=period)

            if df is None or df.empty:
                error_stocks.append(symbol)
                continue
            
            df = calculate_indicators(df, ema_fast, ema_mid, ema_slow, wr_length)
            if df['Buy_Signal'].iloc[-1]:
                qualifying_stocks.append(symbol)
            else:
                not_qualified_stocks.append(symbol)

            time.sleep(0.5)
        
        status_placeholder.empty()
        analyzing_placeholder.empty()

        st.markdown(
            f"<div style='text-align: center; font-size: 18px; color: green;'>{len(stock_symbols)} stocks have been analyzed successfully ✅</div>",
            unsafe_allow_html=True
        )

        # Combine results into a single DataFrame
        max_len = max(len(qualifying_stocks), len(not_qualified_stocks), len(error_stocks))
        combined_results = pd.DataFrame({
            "Qualified Stocks": qualifying_stocks + [""] * (max_len - len(qualifying_stocks)),
            "Unqualified Stocks": not_qualified_stocks + [""] * (max_len - len(not_qualified_stocks)),
            "Lost Stocks": error_stocks + [""] * (max_len - len(error_stocks))
        })

        st.markdown("### Results")
        st.dataframe(combined_results.reset_index(drop=True))

        # Save results to Excel
        with pd.ExcelWriter("results.xlsx", engine="openpyxl") as writer:
            combined_results.to_excel(writer, index=False, sheet_name="Stocks Analysis")

        with open("results.xlsx", "rb") as file:
            st.download_button(
                label="Download Results as Xlsx",
                data=file,
                file_name="HondAlgo_Results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ================= FOOTER =================

st.markdown(
    """
    <style>
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            padding: 10px 0;
            background-color: #333333;
            color: white;
            font-size: 14px;
        }
        .footer-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 20px;
        }
        .footer-center {
            flex: 1;
            text-align: center;
        }
        .footer-right {
            text-align: right;
        }
    </style>
    <div class="footer">
        <div class="footer-content">
            <div class="footer-center">
                Designed by M.Hossam
            </div>
            <div class="footer-right">
                Copyright © 2024 Hondalgo
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
