import pandas as pd
import numpy as np

def run_advanced_technical_analysis(df_ticker, timeframe="Weekly (साप्ताहिक)"):
    """
    Nifty 1000 technical analysis with robust DatetimeIndex & Resampling handling.
    """
    if df_ticker is None or df_ticker.empty:
        print("[TECHNICAL] Warning: Provided DataFrame is empty or None.")
        return None

    # Copy to avoid modifying original dataframe
    df = df_ticker.copy()

    # --- DATETIME INDEX FIX ---
    # Ensure Date column is handled correctly
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date')
    elif not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception as e:
            print(f"[TECHNICAL ERROR] Failed to convert index to DatetimeIndex: {e}")
            return None

    # Sort chronological
    df = df.sort_index()

    # Timeframe Resampling Map
    resample_map = {
        "75m": "75T",
        "Daily (दैनिक)": "D",
        "Weekly (साप्ताहिक)": "W-FRI",
        "Monthly (मासिक)": "ME"
    }
    
    resample_rule = resample_map.get(timeframe, "W-FRI")

    # Dynamic Column Mapping for aggregation
    agg_dict = {}
    for col in ['Open', 'High', 'Low', 'Close', 'Volume', 'Delivery_Pct', 'No_of_Trades']:
        if col in df.columns:
            if col == 'Open':
                agg_dict[col] = 'first'
            elif col == 'High':
                agg_dict[col] = 'max'
            elif col == 'Low':
                agg_dict[col] = 'min'
            elif col == 'Close':
                agg_dict[col] = 'last'
            elif col == 'Volume':
                agg_dict[col] = 'sum'
            elif col == 'Delivery_Pct':
                agg_dict[col] = 'mean'
            elif col == 'No_of_Trades':
                agg_dict[col] = 'sum'

    if not agg_dict or 'Close' not in agg_dict:
        print("[TECHNICAL ERROR] 'Close' column missing in DataFrame.")
        return None

    # Perform Resampling
    tf_df = df.resample(resample_rule).agg(agg_dict).dropna(subset=['Close'])

    # --- Technical Indicators Logic ---
    tf_df['EMA_200'] = tf_df['Close'].ewm(span=200, adjust=False).mean()

    if 'Delivery_Pct' in tf_df.columns:
        tf_df['15_Delivery_DMA'] = tf_df['Delivery_Pct'].rolling(window=15, min_periods=1).mean()
    else:
        tf_df['15_Delivery_DMA'] = np.nan

    # Fair Value Gap (FVG) Calculation
    tf_df['FVG_Bullish'] = (tf_df['Low'] > tf_df['High'].shift(2))
    
    return tf_df

