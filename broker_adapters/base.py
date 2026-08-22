"""
सगळ्या broker adapters (Upstox, Zerodha, Angel One, इ.) साठी common interface.

नवीन broker जोडायचा असेल तर फक्त हा class inherit करून खालील ३ methods
implement करा — बाकी संपूर्ण app (data_provider.py, dashboard) कुठल्याही
बदलाशिवाय नवीन broker वापरू शकेल.
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class BrokerAdapter(ABC):
    """प्रत्येक broker-specific adapter ने हा interface implement करावा."""

    name: str = "base"

    @abstractmethod
    def is_connected(self) -> bool:
        """युजरने हा broker आधीच authenticate/connect केला आहे का?"""
        raise NotImplementedError

    @abstractmethod
    def get_live_ltp(self, symbol: str) -> Optional[float]:
        """
        Live Last Traded Price. broker connected नसेल किंवा
        symbol साठी डेटा उपलब्ध नसेल तर None परत करा (कधीही fake किंमत नाही).
        symbol हा NSE चा exchange-agnostic ticker आहे उदा. 'RELIANCE.NS'.
        """
        raise NotImplementedError

    @abstractmethod
    def get_historical(self, symbol: str, from_date, to_date) -> Optional[pd.DataFrame]:
        """
        उपलब्ध असल्यास broker च्या स्वतःच्या historical API वरून OHLCV.
        कॉलम्स: Date, Open, High, Low, Close, Volume (शक्य असल्यास No_of_Trades, Delivery_Pct).
        उपलब्ध नसेल तर None — तेव्हा data_provider आपोआप free NSE data कडे वळेल.
        """
        raise NotImplementedError

    def display_name(self) -> str:
        return self.name
