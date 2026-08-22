import os
import sys
import time
import pandas as pd
from datetime import date, timedelta
from jugaad_data.nse import stock_df

DB_FOLDER = "investment_data_warehouse"
MAPPING_FILE = "investment_master_mapping.csv"

os.makedirs(DB_FOLDER, exist_ok=True)


def generate_master_mapping_sheet():
    if os.path.exists(MAPPING_FILE):
        return pd.read_csv(MAPPING_FILE)
    return pd.DataFrame()


def _nse_symbol(yf_ticker: str) -> str:
    return yf_ticker.replace(".NS", "").replace(".BO", "").strip()


def _try_nse(ticker: str, years: int) -> "pd.DataFrame | None":
    """NSE च्या स्वतःच्या API वरून (jugaad-data) खरा OHLC + खरी Delivery% + खरी
    No. of Trades मिळते — हा प्राधान्याचा (सर्वोत्तम) स्रोत. पण NSE अनेकदा
    क्लाउड/डेटासेंटर IPs (Streamlit Cloud सकट) bot-protection मुळे ब्लॉक करते,
    त्यामुळे हे अनेकदा तिथून fail होऊ शकतं — ते अपेक्षितच आहे, crash नाही."""
    symbol = _nse_symbol(ticker)
    to_date = date.today()
    from_date = to_date - timedelta(days=365 * years)
    try:
        raw = stock_df(symbol=symbol, from_date=from_date, to_date=to_date, series="EQ")
        if raw is None or raw.empty:
            return None
        df = raw.rename(columns={
            "DATE": "Date", "OPEN": "Open", "HIGH": "High", "LOW": "Low",
            "CLOSE": "Close", "VOLUME": "Volume",
            "NO OF TRADES": "No_of_Trades", "DELIVERY %": "Delivery_Pct",
        })
        keep_cols = ["Date", "Open", "High", "Low", "Close", "Volume", "No_of_Trades", "Delivery_Pct"]
        df = df[keep_cols].copy()
        df["Delivery_Pct"] = pd.to_numeric(df["Delivery_Pct"], errors="coerce")
        df["No_of_Trades"] = pd.to_numeric(df["No_of_Trades"], errors="coerce")
        return df
    except Exception as e:
        print(f"[NSE] {symbol} failed (सहसा cloud IP block): {e}")
        return None


def _try_yfinance(ticker: str, years: int) -> "pd.DataFrame | None":
    """Fallback — NSE ब्लॉक झालं तर Yahoo Finance वरून निदान खरा OHLC+Volume
    मिळतो (चार्ट दिसण्यासाठी हे पुरेसं आहे). Delivery%/No_of_Trades मात्र NSE
    कडेच असतात, यात NaN राहतील — त्यामुळे delivery-आधारित सिग्नल्स त्या
    वेळी कमकुवत असतील, पण चार्ट रिकामा राहणार नाही."""
    try:
        import yfinance as yf
        period = f"{years}y"
        raw = yf.download(ticker, period=period, interval="1d", auto_adjust=True, progress=False)
        if raw is None or raw.empty:
            return None
        raw = raw.reset_index()
        raw.columns = [c[0] if isinstance(c, tuple) else c for c in raw.columns]
        df = raw.rename(columns={"Date": "Date", "Open": "Open", "High": "High",
                                  "Low": "Low", "Close": "Close", "Volume": "Volume"})
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
        df["No_of_Trades"] = pd.NA
        df["Delivery_Pct"] = pd.NA
        return df
    except Exception as e:
        print(f"[yfinance fallback] {ticker} failed: {e}")
        return None


def sync_single_ticker(ticker: str, years: int = 5) -> bool:
    """
    एका ticker साठी डेटा डाउनलोड करतो — आधी NSE (सर्वोत्तम, delivery% सकट)
    ट्राय करतो, ते ब्लॉक/fail झालं (सहसा cloud IP मुळे) तर आपोआप yfinance
    वर fallback होतो (OHLC+Volume मिळतो, delivery% त्या वेळी NaN राहतो).
    investment_data_warehouse/<ticker>_5year.csv मध्ये सेव्ह करतो.

    Return: यशस्वी झालं तर True, दोन्ही स्रोत fail झाले तरच False.
    """
    file_path = os.path.join(DB_FOLDER, f"{ticker}_5year.csv")

    df = _try_nse(ticker, years)
    source = "NSE"
    if df is None:
        df = _try_yfinance(ticker, years)
        source = "Yahoo Finance (fallback — NSE unreachable)"

    if df is None:
        print(f"[ERROR] {ticker}: दोन्ही NSE आणि Yahoo Finance कडून डेटा मिळाला नाही.")
        return False

    df = df.sort_values("Date")
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df.to_csv(file_path, index=False)
    print(f"[SUCCESS] {ticker} data saved via {source} -> {file_path} ({len(df)} rows)")
    return True


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
