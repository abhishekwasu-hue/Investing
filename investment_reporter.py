import os
import pandas as pd
from datetime import datetime

# Import modular blocks safely
import investment_database as db
import investment_macro as macro
import investment_technical as tech
import investment_fundamental as fund

def build_and_dispatch_weekly_report():
    print("[REPORTER] Compiling Final Alpha Long-Term Research Dashboard...")
    
    # 1. Fetch Global Commodities & FPI Flows
    crude, dxy, macro_text = macro.fetch_global_commodity_trends()
    fpi_data = macro.fetch_nsdl_fpi_flow_report()
    
    mapping_df = db.generate_master_mapping_sheet()
    if mapping_df.empty:
        print("[WARNING] Master mapping list is empty. Exiting.")
        return
        
    # 2. Iterate and Screen All Tickers
    for _, row in mapping_df.iterrows():
        file_path = os.path.join(db.DB_FOLDER, f"{row['Ticker']}_5year.csv")
        if not os.path.exists(file_path): 
            continue
        
        df_ticker = pd.read_csv(file_path)
        
        # 🟢 SYNTAX FIX: Passing argument positionally to align exactly with tech engine expectations
        metrics = tech.run_advanced_technical_analysis(df_ticker, "Weekly (साप्ताहिक)")
        if metrics["status"] != "SUCCESS": 
            continue
            
        fund_score, pe, debt, roe, fcf = fund.run_advanced_fundamental_analysis(row['Ticker'])
        
    print(f"--- NIFTY 1000 PRO ENGINE RUN FINISHED: {datetime.now().strftime('%d-%b-%Y')} ---")

if __name__ == "__main__":
    build_and_dispatch_weekly_report()
