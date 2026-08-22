"""
Dashboard/report code ने ह्याच फाईलशी बोलायचं — कुठला broker (किंवा
broker नाहीच) वापरला जातोय हे इथे लपवलेलं असतं.

Logic:
  1. युजरने एखादा broker connect केला असेल (session मध्ये) आणि तो
     is_connected() असेल -> live LTP त्याच्याकडून घे.
  2. Historical OHLC साठी सुद्धा आधी connected broker try कर, तो data देत
     नसेल (None) -> आपोआप free NSE data (investment_data_warehouse/) वर
     fallback कर. यामुळे कुठलाही broker connect नसला तरी app पूर्ण काम करतं.
"""

from typing import Optional
import pandas as pd

from broker_adapters import get_broker_adapter, FreeDataAdapter
from broker_adapters.base import BrokerAdapter

_free_adapter = FreeDataAdapter()


def get_ohlc_data(symbol: str, from_date, to_date, active_broker: Optional[BrokerAdapter] = None) -> pd.DataFrame:
    """active_broker: session मध्ये सध्या connected असलेला adapter (किंवा None)."""
    if active_broker is not None and active_broker.is_connected():
        df = active_broker.get_historical(symbol, from_date, to_date)
        if df is not None and not df.empty:
            return df
        print(f"[data_provider] {active_broker.display_name()} कडून historical data मिळाला नाही, free NSE data वर fallback.")

    df = _free_adapter.get_historical(symbol, from_date, to_date)
    if df is None:
        raise FileNotFoundError(
            f"{symbol} साठी कुठलाही data source उपलब्ध नाही. आधी investment_database.py चालवा."
        )
    return df


def get_live_ltp(symbol: str, active_broker: Optional[BrokerAdapter] = None) -> Optional[float]:
    """Live किंमत फक्त एखादा real broker connected असेल तरच मिळते.
    Free source मध्ये फक्त शेवटच्या EOD close ची किंमत असते (delayed)."""
    if active_broker is not None and active_broker.is_connected():
        ltp = active_broker.get_live_ltp(symbol)
        if ltp is not None:
            return ltp
    return None  # dashboard ने None आल्यास "Live data unavailable — showing delayed price" दाखवावं
