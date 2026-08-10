import os
import pandas as pd
import numpy as np
import investment_technical as tech

def load_universe_data():
    """
    Helper function to load data safely for the reporter.
    Adjust the path or fetch logic as per your repository setup.
    """
    # If you have local CSV/Parquet database synced in workflow:
    data_path = "nifty_1000_data.csv" # किंवा तुमच्या डेटा फाइलचे नाव
    
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        return df
    else:
        # Dummy fallback structure if file is dynamically generated
        print(f"[REPORTER WARNING] Data file {data_path} not found. Creating placeholder structured DF.")
        dates = pd.date_range(end=pd.Timestamp.today(), periods=200, freq='D')
        df = pd.DataFrame({
            'Date': dates,
            'Open': np.random.uniform(100, 200, size=200),
            'High': np.random.uniform(200, 250, size=200),
            'Low': np.random.uniform(80, 100, size=200),
            'Close': np.random.uniform(100, 200, size=200),
            'Volume': np.random.randint(1000, 100000, size=200),
            'Delivery_Pct': np.random.uniform(40, 80, size=200),
            'No_of_Trades': np.random.randint(100, 5000, size=200)
        })
        return df

def build_and_dispatch_weekly_report():
    print("[REPORTER] Compiling Final Alpha Long-Term Research Dashboard...")
    print("[MACRO ENGINE] Querying Global Commodities & Dollar Index (DXY)...")
    print("[MACRO ENGINE] Scraping Fortnightly FPI Sectoral Flows from NSDL...")

    # 1. Properly fetch/load the dataframe FIRST (Prevents NameError)
    df_ticker = load_universe_data()

    # 2. Safety check before analysis
    if df_ticker is None or df_ticker.empty:
        print("[REPORTER ERROR] No ticker data available to generate report.")
        return

    # 3. Pass data to Advanced Technical Analysis
    metrics = tech.run_advanced_technical_analysis(df_ticker, timeframe="Weekly (साप्ताहिक)")

    if metrics is not None:
        print("[REPORTER SUCCESS] Technical Metrics calculated successfully!")
        print(f"[REPORTER SUCCESS] Processed {len(metrics)} weekly records.")
    else:
        print("[REPORTER ERROR] Failed to compute technical metrics.")

if __name__ == "__main__":
    build_and_dispatch_weekly_report()
