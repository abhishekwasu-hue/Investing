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


def sync_single_ticker(ticker: str, years: int = 5) -> bool:
    """
    एका ticker साठी real NSE OHLC + Delivery% डेटा डाउनलोड करून
    investment_data_warehouse/<ticker>_5year.csv मध्ये सेव्ह करतो.

    हे bulk sync_universal_database() आणि on-demand data_provider fallback
    दोघेही वापरतात — जेणेकरून लॉजिक एकाच ठिकाणी राहतो.

    Return: यशस्वी झालं तर True, अन्यथा False (कधीही exception वर crash होत नाही).
    """
    symbol = _nse_symbol(ticker)
    file_path = os.path.join(DB_FOLDER, f"{ticker}_5year.csv")
    to_date = date.today()
    from_date = to_date - timedelta(days=365 * years)

    try:
        # 🟢 NSE च्या स्वतःच्या historical-data API वरून खरा OHLC +
        # खरी 'No. of Trades' आणि खरी 'Delivery %' (COP_DELIV_PERC) मिळते
        raw = stock_df(symbol=symbol, from_date=from_date, to_date=to_date, series="EQ")

        if raw is None or raw.empty:
            print(f"[WARNING] No data received for {symbol} from NSE.")
            return False

        df = raw.rename(columns={
            "DATE": "Date", "OPEN": "Open", "HIGH": "High", "LOW": "Low",
            "CLOSE": "Close", "VOLUME": "Volume",
            "NO OF TRADES": "No_of_Trades", "DELIVERY %": "Delivery_Pct",
        })

        keep_cols = ["Date", "Open", "High", "Low", "Close", "Volume", "No_of_Trades", "Delivery_Pct"]
        df = df[keep_cols].copy()

        # काही जुन्या/कमी-लिक्विड सिक्युरिटीजसाठी Delivery % रिकामी येऊ शकते —
        # ती fake numbers ने भरण्याऐवजी NaN च राहू देतो
        df["Delivery_Pct"] = pd.to_numeric(df["Delivery_Pct"], errors="coerce")
        df["No_of_Trades"] = pd.to_numeric(df["No_of_Trades"], errors="coerce")

        df = df.sort_values("Date")
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

        df.to_csv(file_path, index=False)
        print(f"[SUCCESS] Real NSE data saved for {symbol} -> {file_path} ({len(df)} rows)")
        return True

    except Exception as e:
        print(f"[ERROR] sync_single_ticker failed for {symbol}: {e}")
        return False


def sync_universal_database(years: int = 5):
    """
    सगळ्या mapping sheet मधल्या tickers साठी bulk sync (ऐच्छिक — आता
    app आपोआप on-demand प्रत्येक ticker fetch करते, त्यामुळे हे स्क्रिप्ट
    चालवायलाच हवं असं राहिलेलं नाही. मोठ्या प्रमाणावर एकदाच pre-warm
    करायचं असेल तर उपयोगी).
    """
    print("[REAL DATA ENGINE] Commencing REAL NSE OHLC + Delivery Sync (NSE historical API)...")
    mapping_df = generate_master_mapping_sheet()

    if mapping_df.empty:
        print("[CRITICAL] Master mapping file is missing or empty!")
        return

    tickers = mapping_df['Ticker'].tolist()
    for ticker in tickers:
        print(f"[🌐 NSE REAL DATA] Downloading {years}-year OHLC + Delivery data for: {ticker}")
        sync_single_ticker(ticker, years=years)
        time.sleep(1)  # NSE सर्व्हरवर ब्लॉकिंग टाळण्यासाठी सुरक्षित गॅप

    print("[🏁 COMPLETE] All tickers synced with REAL NSE market data (no random/mock values).")


if __name__ == "__main__":
    sync_universal_database()
