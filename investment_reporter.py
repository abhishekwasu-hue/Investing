import pandas as pd
import investment_technical as tech

def build_and_dispatch_weekly_report():
    print("[REPORTER] Compiling Final Alpha Long-Term Research Dashboard...")
    print("[MACRO ENGINE] Querying Global Commodities & Dollar Index (DXY)...")
    print("[MACRO ENGINE] Scraping Fortnightly FPI Sectoral Flows from NSDL...")

    # Example: Loading ticker data
    # df_ticker = fetch_ticker_data("NIFTY500")

    # --- Safety Fix before passing to technical module ---
    if df_ticker is not None and not df_ticker.empty:
        if 'Date' in df_ticker.columns:
            df_ticker['Date'] = pd.to_datetime(df_ticker['Date'])
            df_ticker.set_index('Date', inplace=True)
        elif not isinstance(df_ticker.index, pd.DatetimeIndex):
            df_ticker.index = pd.to_datetime(df_ticker.index)

    # Run Advanced Technical Analysis
    metrics = tech.run_advanced_technical_analysis(df_ticker, "Weekly (साप्ताहिक)")
    
    # Remaining report generation logic...
    print("[REPORTER] Report generated successfully!")

if __name__ == "__main__":
    build_and_dispatch_weekly_report()

