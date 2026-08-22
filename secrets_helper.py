"""
Streamlit Cloud चे Secrets (`st.secrets`) आणि local `.env`/OS environment
variables — दोन्हीपैकी कुठूनही key वाचणारा एकच common helper. जिथेही API
key/token लागतो (Upstox, Razorpay, इ.) तिथे हाच वापरायचा, जेणेकरून
"Cloud secrets मध्ये टाकलं तरी कोड वाचत नाही" असा गोंधळ पुन्हा होणार नाही.
"""

import os
from typing import Optional


def read_secret(key: str) -> Optional[str]:
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key)
