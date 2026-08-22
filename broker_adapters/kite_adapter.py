"""
Zerodha Kite Connect adapter.

Requires: pip install kiteconnect
युजरने स्वतःचा Kite `access_token` (daily login-flow नंतर मिळणारा) दिला
की हा adapter काम करतो.

⚠️ NOTE: याची exact behavior प्रत्यक्ष kiteconnect SDK आणि Kite च्या
सध्याच्या डॉक्युमेंटेशनशी पडताळून घ्या (https://kite.trade/docs/connect/v3/) —
हे सँडबॉक्समध्ये live टेस्ट करता आलेलं नाही.
"""

from typing import Optional
import pandas as pd

from broker_adapters.base import BrokerAdapter


class KiteAdapter(BrokerAdapter):
    name = "zerodha_kite"

    def __init__(self, api_key: Optional[str] = None, access_token: Optional[str] = None):
        self.api_key = api_key
        self.access_token = access_token
        self._kite = None
        if api_key and access_token:
            try:
                from kiteconnect import KiteConnect
                self._kite = KiteConnect(api_key=api_key)
                self._kite.set_access_token(access_token)
            except ImportError:
                print("[KiteAdapter] 'kiteconnect' package installed नाही — pip install kiteconnect")
            except Exception as e:
                print(f"[KiteAdapter] init failed: {e}")

    def is_connected(self) -> bool:
        return self._kite is not None

    def get_live_ltp(self, symbol: str) -> Optional[float]:
        if not self.is_connected():
            return None
        trading_symbol = self._to_kite_symbol(symbol)
        try:
            quote = self._kite.ltp([trading_symbol])
            entry = quote.get(trading_symbol)
            return float(entry["last_price"]) if entry else None
        except Exception as e:
            print(f"[KiteAdapter] LTP fetch failed for {symbol}: {e}")
            return None

    def get_historical(self, symbol: str, from_date, to_date) -> Optional[pd.DataFrame]:
        # Kite च्या historical API ला numeric instrument_token लागतो, जो
        # instruments() dump मधून एकदा शोधून cache करायला हवा — production मध्ये
        # हा lookup एका instrument-master cache मधून करा, प्रत्येक call ला नाही.
        print("[KiteAdapter] get_historical: instrument_token lookup implement करा (instruments dump वापरून).")
        return None

    def _to_kite_symbol(self, symbol: str) -> str:
        clean = symbol.replace(".NS", "").replace(".BO", "")
        return f"NSE:{clean}"

    def display_name(self) -> str:
        return "Zerodha Kite (Live)"
