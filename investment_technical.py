import os
import numpy as np
import pandas as pd

def run_advanced_technical_analysis(df, tf_mode, index_file_path=None):
    """
    Computes SMC Pivots, Dynamic Timeframe BOS/CHoCH, FVG Imbalances, 
    15-Day Delivery DMA, and Wyckoff Accumulation Patterns with explicit index parsing.
    """
    if len(df) < 40:
        return {
            "status": "ERROR", "tech_score": 50, "regime": "INSUFFICIENT_DATA", 
            "reason": "Insufficient Ledger Data", "swing_highs": [], "swing_lows": [], 
            "fvg_boxes": [], "market_gate": "GREEN_ZONE", "delivery_dma": 50.0, "chart_data": df.reset_index()
        }
        
    # 🔴 Core Pillar 1: 15-Day Moving Delivery Accumulation Cycle (DMA)
    df_recent = df.tail(15)
    delivery_15d_avg = df_recent['Delivery_Pct'].mean() if 'Delivery_Pct' in df_recent.columns else 50.0
    trades_15d_avg = df_recent['No_of_Trades'].mean() if 'No_of_Trades' in df_recent.columns else 10000.0
    historical_trades_avg = df['No_of_Trades'].mean() if 'No_of_Trades' in df.columns else 10000.0
    
    # 🟢 CRITICAL SYSTEM INDEX FIX: Force index parsing to ensure DatetimeIndex compliance
    df_working = df.copy()
    if 'Date' in df_working.columns:
        df_working['Date'] = pd.to_datetime(df_working['Date'])
        df_working.set_index('Date', inplace=True)
    elif not isinstance(df_working.index, pd.DatetimeIndex):
        # If Date is already the index but parsed as strings, force cast it
        df_working.index = pd.to_datetime(df_working.index)
    
    # 🔴 Core Pillar 2: Dynamic Multi-Timeframe Isolation Configuration
    if "75-Minute" in tf_mode:
        resample_rule, window_gap = '75min', 5
    elif "Daily" in tf_mode:
        resample_rule, window_gap = '1D', 10
    elif "Weekly" in tf_mode:
        resample_rule, window_gap = 'W', 8
    else:
        resample_rule, window_gap = 'ME', 6
        
    tf_df = df_working.resample(resample_rule).agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    }).dropna().reset_index()
    
    # Lightweight Performance Optimisation: Limit array sizing to speed up Plotly rendering
    tf_df = tf_df.tail(120).reset_index(drop=True)
    
    if len(tf_df) < 15:
        return {
            "status": "INSUFFICIENT_TF_DATA", "tech_score": 50, "regime": "INSUFFICIENT_DATA", 
            "reason": "Timeframe compression matrix array too small", "swing_highs": [], "swing_lows": [], 
            "fvg_boxes": [], "market_gate": "GREEN_ZONE", "delivery_dma": delivery_15d_avg, "chart_data": tf_df
        }
        
    # --- Option Metrics & Momentum Indexes (RSI 14) ---
    change = tf_df['Close'].diff()
    gain = np.where(change > 0, change, 0)
    loss = np.where(change < 0, -change, 0)
    avg_gain = pd.Series(gain).rolling(window=14, min_periods=1).mean()
    avg_loss = pd.Series(loss).rolling(window=14, min_periods=1).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    tf_df['RSI'] = 100 - (100 / (1 + rs))
    tf_df['EMA_50'] = tf_df['Close'].ewm(span=50, adjust=False).mean()
    
    latest_close = tf_df['Close'].iloc[-1]
    latest_rsi = tf_df['RSI'].iloc[-1]
    swing_highs, swing_lows, fvg_boxes = [], [], []
    
    # 🔴 Core Pillar 3: Wyckoff Phase-C Base Consolidation Triage
    recent_candles = tf_df.tail(6)
    range_pct = (recent_candles['High'].max() - recent_candles['Low'].min()) / (recent_candles['Low'].min() + 1e-10)
    wyckoff_phase_status = "PHASE_B (Consolidation Zone)"
    if range_pct <= 0.08 and tf_df['Close'].iloc[-1] > tf_df['Close'].iloc[-2]:
        wyckoff_phase_status = "PHASE_C (Spring Accumulation Breakout) 🚀"
    
    for i in range(window_gap, len(tf_df) - window_gap):
        if tf_df['High'].iloc[i] == tf_df['High'].iloc[i-window_gap:i+window_gap].max():
            swing_highs.append(tf_df['High'].iloc[i])
        if tf_df['Low'].iloc[i] == tf_df['Low'].iloc[i-window_gap:i+window_gap].min():
            swing_lows.append(tf_df['Low'].iloc[i])
        if i < len(tf_df) - 2 and tf_df['High'].iloc[i] < tf_df['Low'].iloc[i+2]:
            fvg_boxes.append({"top": tf_df['Low'].iloc[i+2], "bottom": tf_df['High'].iloc[i], "type": "BULLISH"})
                
    # 🔴 Core Pillar 4: Nifty 500 Macro Trend Correlation Gate Filter
    market_gate = "GREEN_ZONE"
    if index_file_path and os.path.exists(index_file_path):
        idx_df = pd.read_csv(index_file_path)
        if not idx_df.empty:
            idx_df['Close'] = idx_df['Close'].astype(float)
            idx_ema_200 = idx_df['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
            if idx_df['Close'].iloc[-1] < idx_ema_200:
                market_gate = "RED_ZONE"
                
    # --- Master Quantitative Engine Score Sheet Matrix ---
    quant_score = 40
    if delivery_15d_avg >= 65.0: quant_score += 15
    if trades_15d_avg < historical_trades_avg: quant_score += 15
    if latest_close > tf_df['EMA_50'].iloc[-1]: quant_score += 10
    if 30 <= latest_rsi <= 45: quant_score += 10
    if market_gate == "GREEN_ZONE": quant_score += 10
    
    all_time_high = tf_df['High'].max()
    drop_pct = (all_time_high - latest_close) / (all_time_high + 1e-10)
    triage_status = "STABLE_ACCUMULATION"
    reason_text = f"किंमत सध्या एकाच मर्यादित कप्प्यात ({wyckoff_phase_status}) रेंगाळत असून मोठे खेळाडू हळूहळू माल जमा करत आहेत."
    
    if drop_pct >= 0.05 and drop_pct <= 0.15 and delivery_15d_avg >= 65.0:
        triage_status = "HEALTHY_PRICE_CORRECTION"
        reason_text = f"किंमत सर्वोच्च शिखरावरून {drop_pct*100:.1f}% खाली आली आहे, परंतु १५-दिवसांची डिलिव्हरी सरासरी भक्कम ({delivery_15d_avg:.1f}%) आहे. **हा 'Price Fall' नसून मोठे प्लेयर्स तळाला माल गोळा करत असल्यामुळे आलेले अत्यंत निरोगी 'Price Correction' आहे.**"
    elif drop_pct > 0.15 and trades_15d_avg > historical_trades_avg:
        triage_status = "STRUCTURAL_PRICE_FALL"
        reason_text = f"किंमत शिखरावरून {drop_pct*100:.1f}% ने प्रचंड कोसळली असून व्यवहारांची संख्या वाढली आहे. हे संस्थात्मक गुंतवणूकदारांचे वितरण (Aggressive FPI Distribution) दर्शवते, त्यामुळे सध्या लांब राहावे."
        quant_score -= 30
        
    return {
        "status": "SUCCESS", "score": min(max(quant_score, 10), 100), "regime": triage_status, "reason": reason_text,
        "swing_highs": swing_highs, "swing_lows": swing_lows, "fvg_boxes": fvg_boxes, "market_gate": market_gate,
        "delivery_15d": delivery_15d_avg, "wyckoff_phase": wyckoff_phase_status, "chart_data": tf_df
    }
