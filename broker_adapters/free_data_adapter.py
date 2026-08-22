"""
Default / fallback adapter — कुठलाही broker connect नसेल तरी हा नेहमी उपलब्ध
असतो. फाईल local warehouse मध्ये नसेल तर **आपोआप, त्याच क्षणी** NSE वरून
त्या एका ticker साठी डेटा डाउनलोड करतो (on-demand) — त्यामुळे आधी वेगळं
script चालवायची गरज उरत नाही, आणि deploy केल्यावर लगेच काम करतं.
"""

import os
from typing import Optional
import pandas as pd

from broker_adapters.base import BrokerAdapter

DB_FOLDER = "investment_data_warehouse"


class FreeDataAdapter(BrokerAdapter):
    name = "free_nse_data"

    def is_connected(self) -> bool:
        # हा adapter नेहमी "उपलब्ध" असतो — login लागत नाही
        return True

    def get_live_ltp(self, symbol: str) -> Optional[float]:
        df = self._load(symbol)
        if df is None or df.empty:
            return None
        return float(df["Close"].iloc[-1])

    def get_historical(self, symbol: str, from_date, to_date) -> Optional[pd.DataFrame]:
        df = self._load(symbol)
        if df is None:
            return None
        df["Date"] = pd.to_datetime(df["Date"])
        mask = (df["Date"] >= pd.Timestamp(from_date)) & (df["Date"] <= pd.Timestamp(to_date))
        return df.loc[mask].reset_index(drop=True)

    def _load(self, symbol: str) -> Optional[pd.DataFrame]:
        file_path = os.path.join(DB_FOLDER, f"{symbol}_5year.csv")

        if not os.path.exists(file_path):
            # 🟢 On-demand fetch — फाईल नाही, तर आत्ता NSE वरून आणून सेव्ह करतो
            success = self._fetch_on_demand(symbol)
            if not success:
                return None

        try:
            return pd.read_csv(file_path)
        except Exception as e:
            print(f"[FreeDataAdapter] '{file_path}' वाचता आली नाही: {e}")
            return None

    def _fetch_on_demand(self, symbol: str) -> bool:
        try:
            # circular import टाळण्यासाठी इथेच import (investment_database
            # हा टॉप-लेव्हल मॉड्युल आहे, broker_adapters पॅकेजचा भाग नाही)
            import investment_database as db
            print(f"[FreeDataAdapter] '{symbol}' साठी local data नाही — NSE वरून आत्ता डाउनलोड करतोय...")
            os.makedirs(DB_FOLDER, exist_ok=True)
            return db.sync_single_ticker(symbol, years=5)
        except Exception as e:
            print(f"[FreeDataAdapter] on-demand fetch अयशस्वी ({symbol}): {e}")
            return False

    def display_name(self) -> str:
        return "Free NSE Data (delayed, no login needed)"
