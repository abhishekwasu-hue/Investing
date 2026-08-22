import os
import sys
import time
import pandas as pd
from datetime import date, timedelta
from jugaad_data.nse import stock_df

DB_FOLDER = "investment_data_warehouse"
MAPPING_FILE = "investment_master_mapping.csv"

# फोल्डर अस्तित्वात असल्याची खात्री करणे
os.makedirs(DB_FOLDER, exist_ok=True)


def generate_master_mapping_sheet():
    if os.path.exists(MAPPING_FILE):
        return pd.read_csv(MAPPING_FILE)
    return pd.DataFrame()


def _nse_symbol(yf_ticker: str) -> str:
    """Convert 'RELIANCE.NS' -> 'RELIANCE' (NSE's own historical-data API
    doesn't use the .NS/.BO suffix used by yfinance)."""
    return yf_ticker.replace(".NS", "").replace(".BO", "").strip()


def sync_universal_database(years: int = 5):
    """
    Downloads REAL NSE historical OHLC data along with REAL
    'No. of Trades' and 'Delivery %' columns for every ticker in the
    master mapping sheet, using NSE's own historical-data endpoint
    (via the jugaad-data library) instead of random/mock numbers.

    NOTE: This must be run from an environment that can reach
    nseindia.com (your local machine / a scheduled job) — NSE's
    servers can be slow or occasionally rate-limit; the loop below
    adds a short delay between tickers and skips (rather than crashes)
    on any ticker that fails.
    """
    print("[REAL DATA ENGINE] Commencing REAL NSE OHLC + Delivery Sync (NSE historical API)...")
    mapping_df = generate_master_mapping_sheet()

    if mapping_df.empty:
        print("[CRITICAL] Master mapping file is missing or empty!")
        return

    tickers = mapping_df['Ticker'].tolist()
    to_date = date.today()
    from_date = to_date - timedelta(days=365 * years)

    for ticker in tickers:
        symbol = _nse_symbol(ticker)
        file_path = os.path.join(DB_FOLDER, f"{ticker}_5year.csv")
        print(f"[🌐 NSE REAL DATA] Downloading {years}-year OHLC + Delivery data for: {symbol}")

        try:
            # 🟢 NSE च्या स्वतःच्या historical-data API वरून खरा OHLC +
            # खरी 'No. of Trades' आणि खरी 'Delivery %' (COP_DELIV_PERC) मिळते
            raw = stock_df(symbol=symbol, from_date=from_date, to_date=to_date, series="EQ")

            if raw is None or raw.empty:
                print(f"[WARNING] No data received for {symbol} from NSE. Skipping.")
                continue

            df = raw.rename(columns={
                "DATE": "Date", "OPEN": "Open", "HIGH": "High", "LOW": "Low",
                "CLOSE": "Close", "VOLUME": "Volume",
                "NO OF TRADES": "No_of_Trades", "DELIVERY %": "Delivery_Pct",
            })

            keep_cols = ["Date", "Open", "High", "Low", "Close", "Volume", "No_of_Trades", "Delivery_Pct"]
            df = df[keep_cols].copy()

            # काही जुन्या/कमी-लिक्विड सिक्युरिटीजसाठी Delivery % रिकामी येऊ शकते —
            # ती fake numbers ने भरण्याऐवजी NaN च राहू देतो (पुढे विश्लेषणात हे हाताळलं जातं)
            df["Delivery_Pct"] = pd.to_numeric(df["Delivery_Pct"], errors="coerce")
            df["No_of_Trades"] = pd.to_numeric(df["No_of_Trades"], errors="coerce")

            df = df.sort_values("Date")
            df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

            # 💾 खऱ्या किमती + खरा डिलिव्हरी डेटा फिजिकल फाईल म्हणून सेव्ह करणे
            df.to_csv(file_path, index=False)
            print(f"[SUCCESS] Verified REAL NSE OHLC+Delivery data written for {symbol} -> {file_path} ({len(df)} rows)")

            time.sleep(1)  # NSE सर्व्हरवर ब्लॉकिंग टाळण्यासाठी सुरक्षित गॅप

        except Exception as e:
            print(f"[ERROR] Pipeline failed for {symbol}: {e}")
            continue

    print("[🏁 COMPLETE] All tickers synced with REAL NSE market data (no random/mock values).")


if __name__ == "__main__":
    sync_universal_database()
