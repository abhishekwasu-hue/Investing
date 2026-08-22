"""
Broker adapter registry — नवीन broker जोडायचा असेल तर:
  1. broker_adapters/<broker>_adapter.py मध्ये BrokerAdapter subclass लिहा
  2. खाली AVAILABLE_BROKERS मध्ये एक ओळ जोडा
यापलीकडे data_provider.py किंवा dashboard मध्ये काहीही बदलावं लागत नाही.
"""

from broker_adapters.base import BrokerAdapter
from broker_adapters.free_data_adapter import FreeDataAdapter
from broker_adapters.upstox_adapter import UpstoxAdapter
from broker_adapters.kite_adapter import KiteAdapter
from broker_adapters.angelone_adapter import AngelOneAdapter

# key -> (display label, adapter class)
AVAILABLE_BROKERS = {
    "free": ("Free NSE Data (No login needed)", FreeDataAdapter),
    "upstox": ("Upstox", UpstoxAdapter),
    "zerodha": ("Zerodha Kite", KiteAdapter),
    "angelone": ("Angel One", AngelOneAdapter),
}


def get_broker_adapter(broker_key: str, **credentials) -> BrokerAdapter:
    """
    broker_key: 'free' | 'upstox' | 'zerodha' | 'angelone'
    credentials: त्या adapter च्या __init__ ला लागणारे keyword args
                 (उदा. upstox साठी access_token=..., zerodha साठी
                 api_key=..., access_token=...)
    """
    if broker_key not in AVAILABLE_BROKERS:
        raise ValueError(
            f"Unknown broker '{broker_key}'. Available: {list(AVAILABLE_BROKERS.keys())}"
        )
    _, adapter_cls = AVAILABLE_BROKERS[broker_key]
    return adapter_cls(**credentials)
