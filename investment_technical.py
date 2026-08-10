import pandas as pd
import numpy as np

def run_advanced_technical_analysis(df_ticker, timeframe="Weekly (साप्ताहिक)"):
    """
    Nifty 1000 technical analysis with proper DatetimeIndex handling for resampling.
    """
    if df_ticker is None or df_ticker.empty:
        print("[TECHNICAL] Warning: DataFrame is empty.")
        return None

    # Copy to avoid modifying original dataframe unexpectedly
    df = df_ticker.copy()

    # --- FIX: Ensure Date column exists and is set as DatetimeIndex ---
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date')
    elif not isinstance(df.index, pd.DatetimeIndex):
        # Try converting index directly if Date is already the index
        try:
            df.index = pd.to_datetime(df.index)
        except Exception as e:
            raise TypeError(f"DataFrame index must be a DatetimeIndex for resampling. Error: {e}")

    # Ensure index is sorted chronological
    df = df.sort_index()

    # Determine Resample Rule based on Timeframe
    resample_map = {
        "75m": "75T",
        "Daily (दैनिक)": "D",
        "Weekly (साप्ताहिक)": "W-FRI",
        "Monthly (मासिक)": "ME"  # pandas compatibility
    }
    
    resample_rule = resample_map.get(timeframe, "W-FRI")

    # Perform Resampling for multi-timeframe candles
    tf_df = df.resample(resample_rule).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum' if 'Volume' in df.columns else 'first',
        'Delivery_Pct': 'mean' if 'Delivery_Pct' in df.columns else 'first',
        'No_of_Trades': 'sum' if 'No_of_Trades' in df.columns else 'first'
    }).dropna(subset=['Close'])

    # --- 200 EMA & Technical Logic ---
    tf_df['EMA_200'] = tf_df['Close'].ewm(span=200, adjust=False).mean()
    tf_df['15_Delivery_DMA'] = tf_df['Delivery_Pct'].rolling(window=15, min_periods=1).mean()

    # Fair Value Gap (FVG) Calculation
    tf_df['FVG_Bullish'] = (tf_df['Low'] > tf_df['High'].shift(2))
    
    return tf_df


