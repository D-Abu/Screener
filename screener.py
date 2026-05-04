```python
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

# --- Page Config ---
st.set_page_config(page_title="Shariah Stock Screener", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

# --- FMP API SETUP ---
st.sidebar.markdown("### 🔑 API Configuration")
api_key = st.sidebar.text_input("Enter FMP API Key:", type="password")
st.sidebar.markdown("*Get a free API key at [Financial Modeling Prep](https://financialmodelingprep.com/)*")

st.title("🕌 BSE/NSE Premium Dashboard & Screener")
st.markdown("Powered by Financial Modeling Prep (FMP) | Automated Technicals, Fundamentals, and Shariah Compliance.")

# --- DATA LISTS ---
@st.cache_data
def load_stock_list():
    try:
        df = pd.read_csv("EQUITY_L.csv")
        df['Display'] = df['SYMBOL'] + " - " + df['NAME OF COMPANY']
        return ["✏️ Type Custom Ticker..."] + df['Display'].tolist()
    except Exception:
        return ["✏️ Type Custom Ticker...", "RELIANCE - Reliance", "TCS - TCS", "HDFCBANK - HDFC Bank"]

POPULAR_STOCKS = load_stock_list()
WATCHLIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "SBIN.NS", "ITC.NS"]

# --- FMP FETCH FUNCTIONS ---
@st.cache_data(ttl=3600) 
def fetch_fmp_data(ticker, key):
    # Fetch Company Profile (Sector, Industry, Name)
    profile_url = f"[https://financialmodelingprep.com/api/v3/profile/](https://financialmodelingprep.com/api/v3/profile/){ticker}?apikey={key}"
    bs_url = f"[https://financialmodelingprep.com/api/v3/balance-sheet-statement/](https://financialmodelingprep.com/api/v3/balance-sheet-statement/){ticker}?limit=5&apikey={key}"
    inc_url = f"[https://financialmodelingprep.com/api/v3/income-statement/](https://financialmodelingprep.com/api/v3/income-statement/){ticker}?limit=5&apikey={key}"
    
    try:
        profile = requests.get(profile_url).json()
        info = profile[0] if len(profile) > 0 else {}
        
        bs_data = requests.get(bs_url).json()
        bs = pd.DataFrame(bs_data)
        
        inc_data = requests.get(inc_url).json()
        financials = pd.DataFrame(inc_data)
        
        return info, bs, financials
    except Exception as e:
        return {}, pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_fmp_prices(ticker, key):
    url = f"[https://financialmodelingprep.com/api/v3/historical-price-full/](https://financialmodelingprep.com/api/v3/historical-price-full/){ticker}?apikey={key}"
    try:
        data = requests.get(url).json()
        if 'historical' in data:
            # Convert JSON to DataFrame
            hist_daily = pd.DataFrame(data['historical'])
            hist_daily['date'] = pd.to_datetime(hist_daily['date'])
            # FMP returns newest dates first. We must sort oldest to newest for moving averages!
            hist_daily = hist_daily.sort_values('date').reset_index(drop=True)
            hist_daily.set_index('date', inplace=True)
            
            # Rename 'close' to 'Close' to match our existing logic
            hist_daily.rename(columns={'close': 'Close'}, inplace=True)
            
            # Instantly calculate Weekly data by resampling the daily prices
            hist_weekly = hist_daily['Close'].resample('W').last().to_frame()
            
            return hist_daily, hist_weekly
        return None, None
    except Exception:
        return None, None

def create_price_chart(hist_daily):
    df_chart = hist_daily.tail(252)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['Close'], mode='lines', name='Close Price', line=dict(color='#2962FF', width=2)))
    
    if 'EMA_50' in df_chart.columns:
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA_50'], mode='lines', name='50 DEMA', line=dict(color='#FF6D00', width=1.5, dash='dot')))
    if 'EMA_200' in df_chart.columns:
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA_200'], mode='lines', name='200 DEMA', line=dict(color='#00C853', width=1.5, dash='dot')))
    
    fig.update_layout(title="1-Year Price Trend & EMAs", margin=dict(l=10, r=10, t=40, b=10), height=350, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
    return fig

# --- APP LAYOUT: TABS ---
tab1, tab2 = st.tabs(["📊 Stock Dashboard", "🔎 Live Screener"])

# ==========================================
# TAB 1: SINGLE STOCK DASHBOARD
# ==========================================
with tab1:
    if not api_key:
        st.warning("👈 Please enter your FMP API Key in the sidebar to begin using the application.")
    else:
        with st.container(border=True):
            search_col1, search_col2, search_col3, search_col4 = st.columns([2, 1, 1, 1])

            with search_col1:
                selected_option = st.selectbox("Search Company:", options=POPULAR_STOCKS, index=1, label_visibility="collapsed")

            with search_col2:
                if selected_option == "✏️ Type Custom Ticker...":
                    ticker_input = st.text_input("Enter Ticker:", "RISHABH", label_visibility="collapsed").upper().strip()
                else:
                    ticker_input = selected_option.split(" - ")[0]
                    st.write("")

            with search_col3:
                exchange = st.radio("Exchange:", ("NSE", "BSE"), horizontal=True, label_visibility="collapsed")

            with search_col4:
                analyze_button = st.button("🔍 Analyze Stock", use_container_width=True, type="primary")

        # Ticker format for FMP (matches yfinance!)
        base_symbol = ticker_input.split('.')[0]
        fmp_ticker = f"{base_symbol}.NS" if exchange == "NSE" else f"{base_symbol}.BO"

        if analyze_button:
            with st.spinner(f"Compiling dashboard for {fmp_ticker}..."):
                info, bs, financials = fetch_fmp_data(fmp_ticker, api_key)
                hist_daily, hist_weekly = fetch_fmp_prices(fmp_ticker, api_key)
                
                if bs is None or bs.empty or hist_daily is None or hist_daily.empty:
                    st.error(f"❌ Could not fetch data for {fmp_ticker}. Ensure the API key is correct and the ticker exists.")
                else:
                    current_price = hist_daily['Close'].iloc[-1]
                    
                    # Exponential Moving Averages (DEMA)
                    hist_daily['EMA_50'] = hist_daily['Close'].ewm(span=50, adjust=False).mean()
                    hist_daily['EMA_200'] = hist_daily['Close'].ewm(span=200, adjust=False).mean()
                    
                    company_name = info.get('companyName', ticker_input)
                    sector = info.get('sector', 'Unknown')
                    industry = info.get('industry', 'Unknown')
                    
                    head_col1, head_col2 = st.columns([3, 1])
                    with head_col1:
                        st.markdown(f"## {company_name} ({fmp_ticker})")
                        st.markdown(f"**Sector:** {sector} &nbsp;|&nbsp; **Industry:** {industry}")
                    with head_col2:
                        st.markdown(f"<h2 style='text-align: right; color: #00C853;'>₹{current_price:,.2f}</h2>", unsafe_allow_html=True)
                    
                    row1_col1, row1_col2 = st.columns([2, 1])
                    
                    with row1_col1:
                        with st.container(border=True):
                            st.plotly_chart(create_price_chart(hist_daily), use_container_width=True)
                    
                    with row1_col2:
                        with st.container(border=True):
                            st.markdown("#### 📈 Historical Returns")
                            ret_6m = ((current_price / hist_daily['Close'].iloc[-126]) - 1) * 100 if len(hist_daily) >= 126 else None
                            ret_12m = ((current_price / hist_daily['Close'].iloc[-252]) - 1) * 100 if len(hist_daily) >= 252 else None
                            ret_3y = ((current_price / hist_daily['Close'].iloc[-756]) - 1) * 100 if len(hist_daily) >= 756 else None
                            
                            st.metric("6-Month Return", f"{ret_6m:.2f}%" if ret_6m else "N/A")
                            st.divider()
                            st.metric("12-Month Return", f"{ret_12m:.2f}%" if ret_12m else "N/A")
                            st.divider()
                            st.metric("3-Year Return", f"{ret_3y:.2f}%" if ret_3y else "N/A")

                    # --- FUNDAMENTAL ANALYSIS BLOCK ---
                    with st.container(border=True):
                        st.markdown("#### 🏢 Fundamental Analysis")
                        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
                        
                        try:
                            # FMP returns index 0 as the most recent year
                            net_income_1y = financials['netIncome'].iloc[0]
                            equity_1y = bs['totalStockholdersEquity'].iloc[0]
                            ebit_1y = financials['operatingIncome'].iloc[0]
                            capital_employed_1y = bs['totalAssets'].iloc[0] - bs['totalCurrentLiabilities'].iloc[0]
                            
                            roe_1y = (net_income_1y / equity_1y) * 100 if equity_1y else 0
                            roce_1y = (ebit_1y / capital_employed_1y) * 100 if capital_employed_1y else 0
                            
                            # 3 Years Ago (Index 3 or oldest)
                            idx_3y = min(3, len(financials) - 1)
                            net_income_3y = financials['netIncome'].iloc[idx_3y]
                            equity_3y = bs['totalStockholdersEquity'].iloc[idx_3y]
                            ebit_3y = financials['operatingIncome'].iloc[idx_3y]
                            capital_employed_3y = bs['totalAssets'].iloc[idx_3y] - bs['totalCurrentLiabilities'].iloc[idx_3y]

                            roe_3y = (net_income_3y / equity_3y) * 100 if equity_3y else 0
                            roce_3y = (ebit_3y / capital_employed_3y) * 100 if capital_employed_3y else 0

                        except Exception as e:
                            roe_1y, roce_1y, roe_3y, roce_3y = 0, 0, 0, 0

                        f_col1.metric("ROE (1 Year)", f"{roe_1y:.2f}%")
                        f_col2.metric("ROCE (1 Year)", f"{roce_1y:.2f}%")
                        f_col3.metric("ROE (3 Year)", f"{roe_3y:.2f}%")
                        f_col4.metric("ROCE (3 Year)", f"{roce_3y:.2f}%")
                        
                        st.divider()
                        st.markdown("**Promoter Holding (Last 5 Quarters)**")
                        st.info("⚠️ *Historical quarterly promoter holding API endpoint required to populate this matrix.*")
                        p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns(5)
                        p_col1.metric("Q1 (Current)", "N/A")
                        p_col2.metric("Q2", "N/A")
                        p_col3.metric("Q3", "N/A")
                        p_col4.metric("Q4", "N/A")
                        p_col5.metric("Q5", "N/A")

                    # --- TECHNICAL ANALYSIS BLOCK ---
                    with st.container(border=True):
                        st.markdown("#### ⚙️ Technical Analysis")
                        t_col1, t_col2, t_col3, t_col4 = st.columns(4)
                        
                        ema_50 = hist_daily['EMA_50'].iloc[-1]
                        ema_200 = hist_daily['EMA_200'].iloc[-1]
                        crossover = "🟢 Bullish" if ema_50 > ema_200 else "🔴 Bearish"

                        hist_weekly['WEMA_30'] = hist_weekly['Close'].ewm(span=30, adjust=False).mean()
                        wema_30 = hist_weekly['WEMA_30'].iloc[-1]
                        wema_status = "🟢 Above 30 WEMA" if current_price > wema_30 else "🔴 Below 30 WEMA"

                        high_52w = hist_daily['Close'].tail(252).max()
                        ath = hist_daily['Close'].max()
                        dist_52w = ((current_price / high_52w) - 1) * 100
                        dist_ath = ((current_price / ath) - 1) * 100

                        t_col1.metric("Trend (50 vs 200 DEMA)", crossover)
                        t_col2.metric("Weekly Trend (30 WEMA)", wema_status)
                        t_col3.metric("vs 52W High", f"{dist_52w:.2f}%")
                        t_col4.metric("vs ATH", f"{dist_ath:.2f}%")

                    # --- AAOIFI BLOCK ---
                    with st.container(border=True):
                        st.markdown("#### ⚖️ AAOIFI Financial Ratios")
                        try:
                            # FMP uses straightforward JSON keys
                            total_assets = bs['totalAssets'].iloc[0]
                            total_debt = bs['totalDebt'].iloc[0]
                            cash_and_equiv = bs.get('cashAndCashEquivalents', pd.Series([0])).iloc[0]
                            short_term_investments = bs.get('shortTermInvestments', pd.Series([0])).iloc[0]
                            long_term_investments = bs.get('longTermInvestments', pd.Series([0])).iloc[0]
                            
                            total_revenue = financials['revenue'].iloc[0]
                            interest_income = financials.get('interestIncome', pd.Series([0])).iloc[0]
                            
                            total_cash_investments = cash_and_equiv + short_term_investments
                            interest_bearing_securities = short_term_investments + long_term_investments
                            
                            if total_assets > 0 and total_revenue > 0:
                                debt_to_assets = (total_debt / total_assets) * 100
                                cash_to_assets = (total_cash_investments / total_assets) * 100
                                securities_to_assets = (interest_bearing_securities / total_assets) * 100
                                interest_to_revenue = (interest_income / total_revenue) * 100
                                
                                s_col1, s_col2, s_col3, s_col4 = st.columns(4)
                                s_col1.metric("Debt / Assets (< 33%)", f"{debt_to_assets:.2f}%")
                                s_col2.metric("Cash / Assets (< 33%)", f"{cash_to_assets:.2f}%")
                                s_col3.metric("Securities / Assets (< 33%)", f"{securities_to_assets:.2f}%")
                                s_col4.metric("Interest / Revenue (< 5%)", f"{interest_to_revenue:.2f}%")
                                        
                                if debt_to_assets < 33 and cash_to_assets < 33 and securities_to_assets < 33 and interest_to_revenue < 5:
                                    st.success("🟢 **Verdict: COMPLIANT**")
                                else:
                                    st.error("🔴 **Verdict: NON-COMPLIANT**")
                            else:
                                st.warning("Financial data (Assets/Revenue) is zero or missing.")
                        except Exception as e:
                            st.error("⚠️ Incomplete data from FMP to calculate Shariah ratios.")

# ==========================================
# TAB 2: LIVE SCREENER (FMP Powered)
# ==========================================
with tab2:
    st.markdown("### 🔎 Quick Screener (Watchlist)")
    st.write("Powered by FMP. Scan a predefined watchlist of top stocks based on Technical criteria.")
    
    if not api_key:
        st.warning("Please enter your FMP API Key in the sidebar.")
    else:
        col1, col2, col3 = st.columns(3)
        filter_1 = col1.button("Filter: Above 50 & 200 DEMA", use_container_width=True)
        filter_2 = col2.button("Filter: Above 200 DEMA only", use_container_width=True)
        filter_3 = col3.button("Filter: Above 30 WEMA", use_container_width=True)

        if filter_1 or filter_2 or filter_3:
            results = []
            my_bar = st.progress(0, text="Scanning watchlist...")
            
            for i, ticker in enumerate(WATCHLIST):
                try:
                    my_bar.progress(int(((i + 1) / len(WATCHLIST)) * 100), text=f"Scanning {ticker}...")
                    
                    hist_d, hist_w = fetch_fmp_prices(ticker, api_key)
                    
                    if hist_d is not None and not hist_d.empty:
                        current_price = hist_d['Close'].iloc[-1]
                        
                        ema_50 = hist_d['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                        ema_200 = hist_d['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
                        wema_30 = hist_w['Close'].ewm(span=30, adjust=False).mean().iloc[-1]
                        
                        passed = False
                        if filter_1 and (current_price > ema_50 and current_price > ema_200):
                            passed = True
                        elif filter_2 and (current_price > ema_200):
                            passed = True
                        elif filter_3 and (current_price > wema_30):
                            passed = True
                            
                        if passed:
                            results.append({
                                "Ticker": ticker.replace('.NS', ''),
                                "Price": round(current_price, 2),
                                "50 DEMA": round(ema_50, 2),
                                "200 DEMA": round(ema_200, 2),
                                "30 WEMA": round(wema_30, 2)
                            })
                except Exception as e:
                    pass
                    
            my_bar.empty()
            
            if results:
                st.success(f"Found {len(results)} stocks matching your criteria!")
                st.dataframe(pd.DataFrame(results), use_container_width=True)
            else:
                st.warning("No stocks in the watchlist matched this criteria right now.")
