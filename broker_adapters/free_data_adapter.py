"""
Default / fallback adapter — कुठलाही broker connect नसेल तरी हा नेहमी उपलब्ध
असतो. हा `investment_database.py` ने आधीच डाउनलोड केलेल्या
`investment_data_warehouse/*_5year.csv` फाईल्स वाचतो (real NSE data,
पण live नाही — शेवटच्या sync च्या तारखेपर्यंतच).
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
        # Free source मध्ये live tick नाही — शेवटच्या saved close price
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
            return None
        return pd.read_csv(file_path)

    def display_name(self) -> str:
        return "Free NSE Data (delayed, no login needed)"
