import streamlit as st
import time
import plotly.graph_objects as go
import pandas as pd
from analyzer import TechnicalAnalyzer
from utils import get_min_period, send_to_api, fetch_data

st.set_page_config(page_title="Technical Analysis Dashboard", layout="wide")

# Sidebar
# Sidebar
with st.sidebar:
    st.header("Configuration")

    # Predefined stock list
    stock_options = {
        "Gold Futures": "GC=F",
        "Silver Futures": "SI=F",
        "Crude Oil": "CL=F",
        "Etherium": "ETH-USD",
        "BitCoin" : "BTC-USD",
        "XRPUSD" : "XRP-USD",
        "Tesla": "TSLA",
        "Nifty 50": "^NSEI",
        "Custom": None  # Special option for custom input
    }

    stock_choice = st.selectbox("Select Stock", options=list(stock_options.keys()))

    if stock_choice == "Custom":
        ticker = st.text_input("Enter Custom Symbol", value="AAPL")
    else:
        ticker = stock_options[stock_choice]

    interval = st.selectbox("Interval", options=["1m", "5m", "15m", "30m", "1h", "4h", "1d"], index=2)
    period_input = st.text_input("Period (e.g., 5d, blank for auto)", value="")
    phone_number = st.text_input("Phone Number for Alerts (optional)", value="9544471880")
    auto_refresh = st.checkbox("Auto-refresh every 5 minutes", value=False)
    
    analyzer = TechnicalAnalyzer()
    max_window = max(analyzer.window_sr, analyzer.rsi_window, analyzer.atr_window, 200)
    default_period = get_min_period(interval, max_window * 2)
    period = period_input if period_input else default_period
    
    if st.button("Start Analysis"):
        st.session_state['analyze'] = True
        st.session_state['df'] = None
        st.session_state['signal_info'] = None


# Main view
st.title("Technical Analysis Dashboard")

if 'analyze' in st.session_state and st.session_state['analyze']:
    try:
        df = fetch_data(ticker, interval, period)
        st.session_state['df'] = df
        current_price = df['Close'].iloc[-1].item()
        signal_info = analyzer.generate_signal(df, current_price)
        st.session_state['signal_info'] = signal_info

        # Display key metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Price", f"{signal_info['current_price']:.2f}")
            st.metric("Signal", signal_info['signal'], delta=f"Confidence: {signal_info['confidence']}")
        with col2:
            st.metric("Support", f"{signal_info['support']:.2f}")
            st.metric("Resistance", f"{signal_info['resistance']:.2f}")
        with col3:
            st.metric("RSI", f"{signal_info['rsi']:.2f}")
            st.metric("MACD", f"{signal_info['macd']:.2f}", delta=f"Signal Line: {signal_info['signal_line']:.2f}")

        # Additional metrics
        with st.expander("More Indicators"):
            st.metric("Bollinger Upper", f"{signal_info['bb_upper']:.2f}")
            st.metric("Bollinger Lower", f"{signal_info['bb_lower']:.2f}")
            st.metric("Hold Minutes", signal_info['hold_minutes'])

        # Graphs
        st.subheader("Price Chart with Support/Resistance and Bollinger Bands")
        fig_price = go.Figure()
        fig_price.add_trace(go.Candlestick(x=df.index,
                                           open=df['Open'], high=df['High'],
                                           low=df['Low'], close=df['Close'],
                                           name='Price'))
        fig_price.add_trace(go.Scatter(x=df.index, y=[signal_info['support']] * len(df), mode='lines', name='Support', line=dict(color='green')))
        fig_price.add_trace(go.Scatter(x=df.index, y=[signal_info['resistance']] * len(df), mode='lines', name='Resistance', line=dict(color='red')))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['Close'].rolling(analyzer.bb_window).mean() + df['Close'].rolling(analyzer.bb_window).std() * analyzer.bb_std, mode='lines', name='BB Upper', line=dict(color='orange')))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['Close'].rolling(analyzer.bb_window).mean() - df['Close'].rolling(analyzer.bb_window).std() * analyzer.bb_std, mode='lines', name='BB Lower', line=dict(color='orange')))
        fig_price.update_layout(xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_price, use_container_width=True)

        st.subheader("RSI Chart")
        delta = df['Close'].diff()
        gain = delta.clip(lower=0).rolling(analyzer.rsi_window).mean()
        loss = -delta.clip(upper=0).rolling(analyzer.rsi_window).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df.index, y=rsi_series, mode='lines', name='RSI'))
        fig_rsi.add_trace(go.Scatter(x=df.index, y=[30] * len(df), mode='lines', name='Oversold', line=dict(color='green', dash='dash')))
        fig_rsi.add_trace(go.Scatter(x=df.index, y=[70] * len(df), mode='lines', name='Overbought', line=dict(color='red', dash='dash')))
        st.plotly_chart(fig_rsi, use_container_width=True)

        st.subheader("MACD Chart")
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df.index, y=macd_line, mode='lines', name='MACD'))
        fig_macd.add_trace(go.Scatter(x=df.index, y=signal_line, mode='lines', name='Signal Line'))
        fig_macd.add_trace(go.Bar(x=df.index, y=macd_hist, name='Histogram'))
        st.plotly_chart(fig_macd, use_container_width=True)

        # Send alert if confidence high
        if signal_info['confidence'] > 0.5 and phone_number:
            wamsg = (f"➡ {signal_info['signal']} | {ticker} | Confidence: {signal_info['confidence']} \n"
                     f"Close: {signal_info['current_price']} \n"
                     f"Support: {signal_info['support']} \n"
                     f"Resistance: {signal_info['resistance']} \n"
                     f"RSI: {signal_info['rsi']} \n"
                     f"MACD: {signal_info['macd']} \n"
                     f"Signal Line: {signal_info['signal_line']} \n"
                     f"BB Upper: {signal_info['bb_upper']} \n"
                     f"BB Lower: {signal_info['bb_lower']}")
            send_to_api(phone_number, wamsg)

    except Exception as e:
        st.error(f"Error: {e}")

# Auto-refresh
if auto_refresh and 'analyze' in st.session_state and st.session_state['analyze']:
    time.sleep(300)
    st.rerun()