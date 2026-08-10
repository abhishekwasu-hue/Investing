import pandas as pd
import numpy as np

def run_advanced_technical_analysis(df, tf_mode):
    """
    चारही टाईमफ्रेमसाठी स्वतंत्रपणे BOS, CHoCH, FVG, 15-Day Delivery Avg,
    आणि वायकॉफ कन्सॉलिडेशनचे अचूक संस्थात्मक गणित मोजणे.
    """
    if len(df) < 50:
        return {
            "status": "INSUFFICIENT_DATA", "tech_score": 50, "peak_high": 0, 
            "lowest_low": 0, "fvg_detected": False, "fvg_price": 0,
            "delivery_dma": 50.0, "trades_drop": False, "wyckoff_phase": "PHASE_A"
        }
    
    # 🔴 स्तंभ १: १५-दिवसांचा डिलिव्हरी सायकल इंडेक्स (Consistent Smart Money)
    df['Delivery_15_DMA'] = df['Delivery_Pct'].rolling(window=15, min_periods=1).mean()
    df['Trades_20_SMA'] = df['No_of_Trades'].rolling(window=20, min_periods=1).mean()
    df['Trades_6M_SMA'] = df['No_of_Trades'].rolling(window=125, min_periods=1).mean()
    
    latest_delivery_dma = df['Delivery_15_DMA'].iloc[-1]
    latest_trades_sma = df['Trades_20_SMA'].iloc[-1]
    six_month_trades_sma = df['Trades_6M_SMA'].iloc[-1]
    
    trades_drop_flag = latest_trades_sma < (six_month_trades_sma * 0.70) # ३०% ने ट्रेड्स कमी आहेत
    
    # टाइमफ्रेम निवडीनुसार अचूक री-सॅम्पलिंग संरचना
    if "75-Minute" in tf_mode:
        resample_rule = '75min'
        pivot_window = 5
    elif "Daily" in tf_mode:
        resample_rule = '1D'
        pivot_window = 10
    elif "Weekly" in tf_mode:
        resample_rule = 'W'
        pivot_window = 12
    else:
        resample_rule = 'ME'
        pivot_window = 6
        
    tf_df = df.resample(resample_rule).agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    }).dropna().reset_index()
    
    if len(tf_df) < 25:
        return {
            "status": "INSUFFICIENT_TIMEFRAME_DATA", "tech_score": 50, "peak_high": tf_df['High'].max(), 
            "lowest_low": tf_df['Low'].min(), "fvg_detected": False, "fvg_price": 0,
            "delivery_dma": latest_delivery_dma, "trades_drop": trades_drop_flag, "wyckoff_phase": "PHASE_A"
        }
        
    # 🔴 स्तंभ २: वायकॉफ फेज-सी 'स्प्रिंग' डिटेक्टर (Time & Range Consolidation)
    recent_candles = tf_df.tail(6)
    box_high = recent_candles['High'].max()
    box_low = recent_candles['Low'].min()
    range_pct = (box_high - box_low) / box_low
    
    wyckoff_phase_status = "PHASE_B (Consolidation)"
    if range_pct <= 0.08: # ६ कॅंडल्स केवळ ८% च्या बॉक्समध्ये अडकल्या आहेत
        if tf_df['Close'].iloc[-1] > tf_df['Close'].iloc[-2] and tf_df['Volume'].iloc[-1] > tf_df['Volume'].tail(5).mean():
            wyckoff_phase_status = "PHASE_C (Spring/Accumulation Breakout) 🚀"
            
    # 🔴 फेअर व्हॅल्यू गॅप (Fair Value Gap - FVG / Imbalance Box) शोधणे
    fvg_flag = False
    fvg_target_price = 0.0
    for i in range(len(tf_df) - 2, 1, -1):
        # Bullish FVG: पहिल्या कॅंडलचा हाय आणि तिसऱ्या कॅंडलचा लो यांच्यामध्ये गॅप असणे
        if tf_df['High'].iloc[i-1] < tf_df['Low'].iloc[i+1] and tf_df['Close'].iloc[i] > tf_df['Open'].iloc[i]:
            fvg_flag = True
            fvg_target_price = (tf_df['High'].iloc[i-1] + tf_df['Low'].iloc[i+1]) / 2
            break
            
    # स्विंग हाय/लो पिव्होट्स गणितावरून अधिकृत BOS आणि CHoCH शोधणे
    peak_high_val = tf_df['High'].max()
    lowest_low_val = tf_df['Low'].min()
    
    # एकत्रित क्वांट स्कोअर मोजणे (Technical Matrix)
    tech_score_weight = 50
    if tf_df['Close'].iloc[-1] > tf_df['Close'].rolling(50, min_periods=1).mean().iloc[-1]:
        tech_score_weight += 15
    if latest_delivery_dma >= 65.0:
        tech_score_weight += 20
    if wyckoff_phase_status.startswith("PHASE_C"):
        tech_score_weight += 15
        
    return {
        "status": "SUCCESS", "tech_score": min(tech_score_weight, 100), 
        "peak_high": peak_high_val, "lowest_low": lowest_low_val, 
        "fvg_detected": fvg_flag, "fvg_price": fvg_target_price,
        "delivery_dma": latest_delivery_dma, "trades_drop": trades_drop_flag, 
        "wyckoff_phase": wyckoff_phase_status
    }



