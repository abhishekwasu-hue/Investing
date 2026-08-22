"""
Angel One (SmartAPI) adapter.

Requires: pip install smartapi-python
⚠️ NOTE: हे structure म्हणून बरोबर आहे, पण exact response format
सध्याच्या SmartAPI डॉक्युमेंटेशनशी पडताळून घ्या
(https://smartapi.angelbroking.com/docs) — सँडबॉक्समध्ये live टेस्ट करता
आलेलं नाही.
"""

from typing import Optional
import pandas as pd

from broker_adapters.base import BrokerAdapter


class AngelOneAdapter(BrokerAdapter):
    name = "angel_one"

    def __init__(self, api_key: Optional[str] = None, session_token: Optional[str] = None,
                 feed_token: Optional[str] = None):
        self.api_key = api_key
        self.session_token = session_token
        self.feed_token = feed_token
        self._client = None
        if api_key and session_token:
            try:
                from SmartApi import SmartConnect
                self._client = SmartConnect(api_key=api_key)
                self._client.setAccessToken(session_token)
                if feed_token:
                    self._client.setFeedToken(feed_token)
            except ImportError:
                print("[AngelOneAdapter] 'smartapi-python' installed नाही — pip install smartapi-python")
            except Exception as e:
                print(f"[AngelOneAdapter] init failed: {e}")

    def is_connected(self) -> bool:
        return self._client is not None

    def get_live_ltp(self, symbol: str) -> Optional[float]:
        if not self.is_connected():
            return None
        try:
            clean = symbol.replace(".NS", "").replace(".BO", "")
            # SmartAPI ला exact 'symboltoken' लागतो — instrument master
            # (https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json)
            # वरून एकदा lookup करून cache करा; इथे placeholder ठेवलंय.
            print(f"[AngelOneAdapter] symboltoken lookup implement करा: {clean}")
            return None
        except Exception as e:
            print(f"[AngelOneAdapter] LTP fetch failed for {symbol}: {e}")
            return None

    def get_historical(self, symbol: str, from_date, to_date) -> Optional[pd.DataFrame]:
        print("[AngelOneAdapter] get_historical: symboltoken lookup + candleData API implement करा.")
        return None

    def display_name(self) -> str:
        return "Angel One (Live)"
