import os
import numpy as np
import pandas as pd


def compute_supertrend(df: pd.DataFrame, atr_period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
    """
    Supertrend — ATR (Average True Range) आधारित classic trend-following
    indicator. किंमत Supertrend line च्या वर असेल तर uptrend (bullish),
    खाली असेल तर downtrend (bearish). df ला ATR/Supertrend/Supertrend_Trend
    कॉलम्स जोडून परत करतो (मूळ df बदलत नाही, copy वर काम करतो).

    Trend=1 म्हणजे bullish (uptrend), Trend=-1 म्हणजे bearish (downtrend).
    हे path-dependent गणित आहे (आजचा निर्णय कालच्यावर अवलंबून) — त्यामुळे
    row-by-row loop लागतो, पूर्णपणे vectorize करता येत नाही.
    """
    df = df.copy().reset_index(drop=True)
    high, low, close = df["High"], df["Low"], df["Close"]

    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr = tr.rolling(window=atr_period, min_periods=1).mean()

    hl2 = (high + low) / 2
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    supertrend = pd.Series(index=df.index, dtype=float)
    trend = pd.Series(index=df.index, dtype=int)

    for i in range(len(df)):
        if i == 0:
            final_upper.iloc[i] = basic_upper.iloc[i]
            final_lower.iloc[i] = basic_lower.iloc[i]
            trend.iloc[i] = -1  # सुरुवात downtrend गृहीत धरून (arbitrary पण consistent)
            supertrend.iloc[i] = final_upper.iloc[i]
            continue

        final_upper.iloc[i] = (
            basic_upper.iloc[i]
            if (basic_upper.iloc[i] < final_upper.iloc[i - 1] or close.iloc[i - 1] > final_upper.iloc[i - 1])
            else final_upper.iloc[i - 1]
        )
        final_lower.iloc[i] = (
            basic_lower.iloc[i]
            if (basic_lower.iloc[i] > final_lower.iloc[i - 1] or close.iloc[i - 1] < final_lower.iloc[i - 1])
            else final_lower.iloc[i - 1]
        )

        if trend.iloc[i - 1] == -1 and close.iloc[i] > final_upper.iloc[i]:
            trend.iloc[i] = 1
        elif trend.iloc[i - 1] == 1 and close.iloc[i] < final_lower.iloc[i]:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i - 1]

        supertrend.iloc[i] = final_lower.iloc[i] if trend.iloc[i] == 1 else final_upper.iloc[i]

    df["ATR"] = atr
    df["Supertrend"] = supertrend
    df["Supertrend_Trend"] = trend
    return df


def detect_supertrend_flip(df: pd.DataFrame, atr_period: int = 10, multiplier: float = 3.0) -> dict:
    """
    Supertrend trend-flip डिटेक्ट करतो — काल आणि आज trend वेगळा असेल
    तरच (flipped=True) सिग्नल देतो, नुसता सध्याचा trend सांगत नाही
    (तो रोज सेमच राहील, तो 'नवीन' सिग्नल नाही).
    """
    if df is None or len(df) < atr_period + 2:
        return {"flipped": False, "direction": None, "supertrend_value": None, "close": None}

    st_df = compute_supertrend(df, atr_period, multiplier)
    if len(st_df) < 2:
        return {"flipped": False, "direction": None, "supertrend_value": None, "close": None}

    current_trend = int(st_df["Supertrend_Trend"].iloc[-1])
    prev_trend = int(st_df["Supertrend_Trend"].iloc[-2])
    flipped = current_trend != prev_trend

    return {
        "flipped": bool(flipped),
        "direction": ("BULLISH" if current_trend == 1 else "BEARISH") if flipped else None,
        "current_trend": "BULLISH" if current_trend == 1 else "BEARISH",
        "supertrend_value": round(float(st_df["Supertrend"].iloc[-1]), 2),
        "close": round(float(st_df["Close"].iloc[-1]), 2),
    }


def compute_support_resistance_levels(swing_highs: list, swing_lows: list, tolerance_pct: float = 1.5) -> list:
    """
    जवळपासचे swing highs/lows एकत्र clustered करून खरे S/R levels काढतो.
    एकाच किमतीभोवती किंमत किती वेळा (touch_count) परत आली यावरून strength
    ठरतो — जास्त touches = जास्त probability, तो level जास्त महत्त्वाचा
    (chart वर जाड/ठळक रेषा, टेबलमध्ये वरती).

    tolerance_pct: याच्या आत असलेले swing points एकाच level चा भाग मानले
    जातात (उदा. 1.5% म्हणजे ₹100 आणि ₹101.4 एकाच cluster मध्ये).
    """
    def _cluster(values, level_type):
        if not values:
            return []
        sorted_vals = sorted(values)
        clusters = []
        current = [sorted_vals[0]]
        for v in sorted_vals[1:]:
            if current and abs(v - current[-1]) / current[-1] * 100 <= tolerance_pct:
                current.append(v)
            else:
                clusters.append(current)
                current = [v]
        clusters.append(current)

        result = []
        for c in clusters:
            avg_price = sum(c) / len(c)
            touch_count = len(c)
            if touch_count >= 4:
                strength = "Strong"
            elif touch_count >= 2:
                strength = "Moderate"
            else:
                strength = "Weak"
            result.append({
                "price": round(avg_price, 2),
                "type": level_type,
                "touch_count": touch_count,
                "strength": strength,
            })
        return result

    levels = _cluster(swing_highs, "Resistance") + _cluster(swing_lows, "Support")
    levels.sort(key=lambda x: x["touch_count"], reverse=True)
    return levels


def detect_price_volume_breakout(tf_df: pd.DataFrame, lookback: int = 10, volume_multiplier: float = 1.5) -> dict:
    """
    Price + Volume Breakout — क्लासिक तांत्रिक सेटअप.

    लॉजिक:
      1. Resistance = मागच्या `lookback` बार्सचा (सध्याचा बार सोडून) सर्वोच्च High
      2. Price breakout = सध्याचा Close त्या resistance च्या वर बंद झाला
      3. Volume confirmation = सध्याचा Volume मागच्या `lookback` बार्सच्या
         सरासरी Volume च्या किमान `volume_multiplier` पट आहे

    दोन्ही खरं असेल तरच 'confirmed breakout' (is_breakout=True) — नुसता
    price breakout कमी volume वर झाला (is_price_breakout_only=True) तर तो
    कमकुवत/संशयास्पद मानला जातो, कारण institutional सहभागाशिवाय होणारे
    breakouts अनेकदा टिकत नाहीत (false breakout).

    कुठल्याही resampled timeframe वर वापरता येतं — Weekly साठी सर्वात
    प्रचलित (lookback=10 आठवडे साधारण standard आहे), पण Daily/Monthly
    वरही तेच लॉजिक चालतं.
    """
    if tf_df is None or len(tf_df) < lookback + 2:
        return {
            "is_breakout": False, "is_price_breakout_only": False,
            "resistance_level": None, "current_close": None, "volume_ratio": None,
        }

    window = tf_df.iloc[-(lookback + 1):-1]  # सध्याचा बार वगळून मागचे lookback बार्स
    resistance = float(window["High"].max())
    avg_volume = float(window["Volume"].mean())

    current = tf_df.iloc[-1]
    current_close = float(current["Close"])
    current_volume = float(current["Volume"])

    price_breakout = current_close > resistance
    volume_ratio = round(current_volume / avg_volume, 2) if avg_volume > 0 else None
    volume_confirmed = volume_ratio is not None and volume_ratio >= volume_multiplier

    return {
        "is_breakout": bool(price_breakout and volume_confirmed),
        "is_price_breakout_only": bool(price_breakout and not volume_confirmed),
        "resistance_level": round(resistance, 2),
        "current_close": round(current_close, 2),
        "volume_ratio": volume_ratio,
    }

def run_advanced_technical_analysis(df, tf_mode, index_file_path=None):
    if len(df) < 40:
        return {
            "status": "ERROR", "tech_score": 50, "regime": "INSUFFICIENT_DATA", 
            "reason": "Insufficient Data Pool", "swing_highs": [], "swing_lows": [], 
            "fvg_boxes": [], "market_gate": "GREEN_ZONE", "delivery_dma": 50.0, "chart_data": df.reset_index(),
            "breakout": None, "supertrend": None,
        }
        
    df_recent = df.tail(15)
    delivery_15d_avg = df_recent['Delivery_Pct'].mean() if 'Delivery_Pct' in df_recent.columns else 50.0
    trades_15d_avg = df_recent['No_of_Trades'].mean() if 'No_of_Trades' in df_recent.columns else 10000.0
    historical_trades_avg = df['No_of_Trades'].mean() if 'No_of_Trades' in df.columns else 10000.0
    
    df_working = df.copy()
    if 'Date' in df_working.columns:
        df_working['Date'] = pd.to_datetime(df_working['Date'])
        df_working.set_index('Date', inplace=True)
    elif not isinstance(df_working.index, pd.DatetimeIndex):
        df_working.index = pd.to_datetime(df_working.index)
    
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
    
    # वेग वाढवण्यासाठी डेटा नियंत्रित करणे (लेटेस्ट १२० ओळी)
    tf_df = tf_df.tail(120).reset_index(drop=True)
    
    if len(tf_df) < 15:
        return {
            "status": "INSUFFICIENT_TF_DATA", "tech_score": 50, "regime": "INSUFFICIENT_DATA", 
            "reason": "Timeframe compression matrix array too small", "swing_highs": [], "swing_lows": [], 
            "fvg_boxes": [], "market_gate": "GREEN_ZONE", "delivery_dma": delivery_15d_avg, "chart_data": tf_df,
            "breakout": None, "supertrend": None,
        }
        
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
                
    market_gate = "GREEN_ZONE"
    if index_file_path and os.path.exists(index_file_path):
        idx_df = pd.read_csv(index_file_path)
        if not idx_df.empty:
            idx_df['Close'] = idx_df['Close'].astype(float)
            idx_ema_200 = idx_df['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
            if idx_df['Close'].iloc[-1] < idx_ema_200:
                market_gate = "RED_ZONE"
                
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
        reason_text = f"किंमत शिखरावरून {drop_pct*100:.1f}% ने प्रचंड कोसळली असून व्यवहारांची संख्या वाढली आहे. ऐतिहासिकदृष्ट्या हा पॅटर्न संस्थात्मक वितरणाशी (institutional distribution) जुळतो — याला उच्च-जोखमीचा (high-risk) झोन मानला जातो. हे केवळ डेटा-पॅटर्न विश्लेषण आहे, गुंतवणूक सल्ला नाही."
        quant_score -= 30
        
    breakout_info = detect_price_volume_breakout(tf_df, lookback=10, volume_multiplier=1.5)
    supertrend_info = detect_supertrend_flip(tf_df, atr_period=10, multiplier=3.0)

    return {
        "status": "SUCCESS", "score": min(max(quant_score, 10), 100), "regime": triage_status, "reason": reason_text,
        "swing_highs": swing_highs, "swing_lows": swing_lows, "fvg_boxes": fvg_boxes, "market_gate": market_gate,
        "delivery_15d": delivery_15d_avg, "wyckoff_phase": wyckoff_phase_status, "chart_data": tf_df,
        "breakout": breakout_info, "supertrend": supertrend_info,
    }
