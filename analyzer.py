import pandas as pd
import numpy as np

class TechnicalAnalyzer:
    def __init__(self, window_sr=20, rsi_window=14, atr_window=14, bb_window=20, bb_std=2):
        self.window_sr = window_sr
        self.rsi_window = rsi_window
        self.atr_window = atr_window
        self.bb_window = bb_window
        self.bb_std = bb_std

    def support_resistance(self, df):
        support = df['Low'].rolling(self.window_sr).min().iloc[-1].item()
        resistance = df['High'].rolling(self.window_sr).max().iloc[-1].item()
        return support, resistance

    def rsi(self, df):
        delta = df['Close'].diff()
        gain = delta.clip(lower=0).rolling(self.rsi_window).mean()
        loss = -delta.clip(upper=0).rolling(self.rsi_window).mean()
        rs = gain / loss
        rsi_val = (100 - (100 / (1 + rs))).iloc[-1].item()
        rsi_slope = ((100 - (100 / (1 + rs))).iloc[-1] - (100 - (100 / (1 + rs))).iloc[-2]).item()
        return rsi_val, rsi_slope

    def macd(self, df, short=12, long=26, signal=9):
        exp1 = df['Close'].ewm(span=short, adjust=False).mean()
        exp2 = df['Close'].ewm(span=long, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        macd_val = macd_line.iloc[-1].item()
        signal_val = signal_line.iloc[-1].item()
        macd_hist = macd_line - signal_line
        hist_slope = (macd_hist.iloc[-1] - macd_hist.iloc[-2]).item()
        return macd_val, signal_val, hist_slope

    def atr(self, df):
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(self.atr_window).mean().iloc[-1].item()

    def bollinger_bands(self, df):
        sma = df['Close'].rolling(self.bb_window).mean()
        std = df['Close'].rolling(self.bb_window).std()
        upper = sma + std * self.bb_std
        lower = sma - std * self.bb_std
        return upper.iloc[-1].item(), lower.iloc[-1].item()

    def trend_filter(self, df):
        ema50 = df['Close'].ewm(span=50).mean().iloc[-1].item()
        ema200 = df['Close'].ewm(span=200).mean().iloc[-1].item()
        return ema50 > ema200, ema50 < ema200  # trend_up, trend_down

    def generate_signal(self, df, current_price):
        support, resistance = self.support_resistance(df)
        rsi_val, rsi_slope = self.rsi(df)
        macd_val, signal_val, hist_slope = self.macd(df)
        atr_val = self.atr(df)
        bb_upper, bb_lower = self.bollinger_bands(df)
        trend_up, trend_down = self.trend_filter(df)

        # Skip if market too quiet
        if atr_val < (df['Close'].iloc[-1].item() * 0.0015):  # Adjusted threshold for better sensitivity
            current_price = df['Close'].iloc[-1].item()
            
            # RSI calculation
            delta = df['Close'].diff()
            gain = delta.clip(lower=0).rolling(self.rsi_window).mean()
            loss = -delta.clip(upper=0).rolling(self.rsi_window).mean()
            rsi_val = (100 - (100 / (1 + gain / loss))).iloc[-1].item()
            
            return {
                "signal": "HOLD",
                "confidence": 0.5,
                "support": round(support, 2),
                "resistance": round(resistance, 2),
                "rsi": round(rsi_val, 2),
                "macd": 0.0,
                "signal_line": 0.0,
                "bb_upper": round(bb_upper, 2),
                "bb_lower": round(bb_lower, 2),
                "current_price": round(current_price, 2),
                "hold_minutes": 0
            }

        score_buy = 0
        score_sell = 0

        # Support/Resistance with tighter bounds
        if current_price <= support * 1.005:
            score_buy += 0.35
        if current_price >= resistance * 0.995:
            score_sell += 0.35

        # RSI with slope and adjusted levels
        if rsi_val < 35 and rsi_slope > 0.1:  # Slightly higher oversold threshold and positive slope requirement
            score_buy += 0.25
        elif rsi_val > 65 and rsi_slope < -0.1:
            score_sell += 0.25

        # MACD with stronger confirmation
        if macd_val > signal_val and hist_slope > 0.01:
            score_buy += 0.25
        elif macd_val < signal_val and hist_slope < -0.01:
            score_sell += 0.25

        # Bollinger Bands
        if current_price < bb_lower * 1.005:
            score_buy += 0.2
        if current_price > bb_upper * 0.995:
            score_sell += 0.2

        # Trend filter with stronger penalty
        if score_buy > 0 and not trend_up:
            score_buy *= 0.6  # Slightly less reduction
        if score_sell > 0 and not trend_down:
            score_sell *= 0.6

        # Determine signal with higher confidence threshold
        if score_buy > score_sell + 0.1:
            signal = "BUY"
            confidence = score_buy
            hold_minutes = 20  # Adjusted hold time
        elif score_sell > score_buy + 0.1:
            signal = "SELL"
            confidence = score_sell
            hold_minutes = 20
        else:
            signal = "HOLD"
            confidence = max(score_buy, score_sell)
            hold_minutes = 0

        return {
            "signal": signal,
            "confidence": round(confidence, 2),
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "rsi": round(rsi_val, 2),
            "macd": round(macd_val, 2),
            "signal_line": round(signal_val, 2),
            "bb_upper": round(bb_upper, 2),
            "bb_lower": round(bb_lower, 2),
            "current_price": round(current_price, 2),
            "hold_minutes": hold_minutes
        }