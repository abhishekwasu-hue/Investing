"""
Upstox adapter — तुमच्या आधीच्या OAuth2 स्क्रिप्टमधून मिळालेला access_token
इथे वापरला जातो (साधारणपणे .env / st.secrets मधून वाचला जातो).

⚠️ NOTE: Upstox चं SDK/endpoint्स वेळोवेळी बदलू शकतात — प्रत्यक्ष वापरण्याआधी
https://upstox.com/developer/api-documentation शी एकदा पडताळून घ्या.
इथला कोड योग्य structure/pattern दाखवतो, पण live टेस्ट सँडबॉक्समध्ये करता
येत नाही (nseindia/upstox डोमेन्स इथून reachable नाहीत).
"""

import os
from typing import Optional
import pandas as pd
import requests

from broker_adapters.base import BrokerAdapter

UPSTOX_BASE_URL = "https://api.upstox.com/v2"


class UpstoxAdapter(BrokerAdapter):
    name = "upstox"

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.environ.get("UPSTOX_ACCESS_TOKEN")

    def is_connected(self) -> bool:
        return bool(self.access_token)

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    def get_live_ltp(self, symbol: str) -> Optional[float]:
        if not self.is_connected():
            return None
        instrument_key = self._to_instrument_key(symbol)
        try:
            resp = requests.get(
                f"{UPSTOX_BASE_URL}/market-quote/ltp",
                headers=self._headers(),
                params={"instrument_key": instrument_key},
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            first_key = next(iter(data), None)
            if not first_key:
                return None
            return float(data[first_key]["last_price"])
        except Exception as e:
            print(f"[UpstoxAdapter] LTP fetch failed for {symbol}: {e}")
            return None

    def get_historical(self, symbol: str, from_date, to_date) -> Optional[pd.DataFrame]:
        if not self.is_connected():
            return None
        instrument_key = self._to_instrument_key(symbol)
        try:
            url = (
                f"{UPSTOX_BASE_URL}/historical-candle/{instrument_key}/day/"
                f"{to_date}/{from_date}"
            )
            resp = requests.get(url, headers=self._headers(), timeout=10)
            resp.raise_for_status()
            candles = resp.json().get("data", {}).get("candles", [])
            if not candles:
                return None
            df = pd.DataFrame(
                candles,
                columns=["Date", "Open", "High", "Low", "Close", "Volume", "OI"],
            )
            df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
            return df.sort_values("Date").reset_index(drop=True)
        except Exception as e:
            print(f"[UpstoxAdapter] historical fetch failed for {symbol}: {e}")
            return None

    def _to_instrument_key(self, symbol: str) -> str:
        """'RELIANCE.NS' -> Upstox instrument_key, e.g. 'NSE_EQ|RELIANCE'.
        प्रत्यक्षात Upstox च्या instrument master CSV वरून exact key मॅप करणं
        जास्त विश्वासार्ह आहे — हे इथे सोपं ठेवलंय, production मध्ये
        instrument master लोड करून cache करा."""
        clean = symbol.replace(".NS", "").replace(".BO", "")
        return f"NSE_EQ|{clean}"

    def display_name(self) -> str:
        return "Upstox (Live)"
