import streamlit as st
import yfinance as yf
import pandas as pd

# --- Page Config ---
st.set_page_config(page_title="NSE Market Screener", layout="wide")
st.title("🔎 Live Bulk Market Screener")

# --- 1. LOAD ALL 5000+ STOCKS FROM CSV ---
@st.cache_data
def get_all_nse_tickers():
    try:
        # Read the official NSE list
        df = pd.read_csv("EQUITY_L.csv")
        # Extract the symbols and append '.NS' for Yahoo Finance
        all_symbols = [str(sym) + ".NS" for sym in df['SYMBOL'].tolist()]
        return all_symbols
    except Exception as e:
        st.error(f"Could not load EQUITY_L.csv. Please ensure it is in the same folder. Error: {e}")
        # Fallback watchlist if file is missing
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]

ALL_NSE_TICKERS = get_all_nse_tickers()

# --- 2. SCREENER UI & CONTROLS ---
st.write(f"Database loaded with **{len(ALL_NSE_TICKERS)}** total NSE stocks.")

# The Scan Limit Slider: Protects your app from timing out by letting you control the batch size
scan_limit = st.slider(
    "How many stocks do you want to scan today?", 
    min_value=10, 
    max_value=len(ALL_NSE_TICKERS), 
    value=100, 
    step=50,
    help="Scanning all 5000+ stocks can take several minutes. Start small to test!"
)

# Slice the massive list down to the user's selected limit
tickers_to_scan = ALL_NSE_TICKERS[:scan_limit]

col1, col2, col3 = st.columns(3)
filter_1 = col1.button("Filter: Above 50 & 200 DEMA", use_container_width=True)
filter_2 = col2.button("Filter: Above 200 DEMA only", use_container_width=True)
filter_3 = col3.button("Filter: Above 30 WEMA", use_container_width=True)

# --- 3. BULK DOWNLOAD & PROCESSING LOGIC ---
if filter_1 or filter_2 or filter_3:
    results = []
    
    with st.spinner(f"Requesting data for {scan_limit} stocks from Yahoo Finance. Please wait..."):
        # Download all data in a single massive network request
        # 'threads=True' allows yfinance to download faster using multiple connections
        hist_d_bulk = yf.download(tickers_to_scan, period="1y", interval="1d", progress=False, threads=True)
        hist_w_bulk = yf.download(tickers_to_scan, period="2y", interval="1wk", progress=False, threads=True)
        
        # Check if download succeeded and 'Close' data exists
        if 'Close' in hist_d_bulk.columns and 'Close' in hist_w_bulk.columns:
            close_prices_d = hist_d_bulk['Close']
            close_prices_w = hist_w_bulk['Close']
            
            # Use a progress bar for the mathematical calculations
            calc_bar = st.progress(0, text="Calculating Moving Averages...")
            
            for i, ticker in enumerate(tickers_to_scan):
                # Update progress bar
                calc_bar.progress(int(((i + 1) / len(tickers_to_scan)) * 100), text=f"Analyzing {ticker}...")
                
                try:
                    # SAFEGUARD: Check if the ticker actually returned data from Yahoo
                    if ticker in close_prices_d.columns and ticker in close_prices_w.columns:
                        
                        # Isolate the specific stock and drop empty days (NaNs)
                        daily_close = close_prices_d[ticker].dropna()
                        weekly_close = close_prices_w[ticker].dropna()
                        
                        # Only proceed if we have enough data points
                        if not daily_close.empty and not weekly_close.empty and len(daily_close) > 200:
                            current_price = daily_close.iloc[-1]
                            
                            # Calculate moving averages instantly
                            ema_50 = daily_close.ewm(span=50, adjust=False).mean().iloc[-1]
                            ema_200 = daily_close.ewm(span=200, adjust=False).mean().iloc[-1]
                            wema_30 = weekly_close.ewm(span=30, adjust=False).mean().iloc[-1]
                            
                            # Filter Logic
                            passed = False
                            if filter_1 and (current_price > ema_50 and current_price > ema_200):
                                passed = True
                            elif filter_2 and (current_price > ema_200):
                                passed = True
                            elif filter_3 and (current_price > wema_30):
                                passed = True
                                
                            # If it passes, save the data!
                            if passed:
                                results.append({
                                    "Ticker": ticker.replace('.NS', ''),
                                    "Price": round(current_price, 2),
                                    "50 DEMA": round(ema_50, 2),
                                    "200 DEMA": round(ema_200, 2),
                                    "30 WEMA": round(wema_30, 2)
                                })
                except Exception as e:
                    # If math fails on a weird stock, quietly skip it and keep the app running
                    pass 
            
            # Clear the progress bar when done
            calc_bar.empty()
            
            # --- 4. DISPLAY RESULTS ---
            if results:
                st.success(f"Scan complete! Found {len(results)} stocks matching your criteria out of {scan_limit} scanned.")
                st.dataframe(pd.DataFrame(results), use_container_width=True)
            else:
                st.warning(f"Scan complete. No stocks out of the {scan_limit} scanned matched this criteria right now.")
        
        else:
            st.error("Failed to download price data. Yahoo Finance might be temporarily rate-limiting your connection.")
