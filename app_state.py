"""
सगळ्या पेजेसमध्ये common sidebar (sector/ticker/timeframe/broker) आणि तो
निवडलेला state — एकाच ठिकाणी, जेणेकरून प्रत्येक page मध्ये duplicate कोड
लिहावा लागत नाही आणि निवड सगळीकडे सुसंगत राहते.
"""

import os
import streamlit as str_app
import pandas as pd

from broker_adapters import get_broker_adapter, AVAILABLE_BROKERS
from broker_adapters.free_data_adapter import FreeDataAdapter

MAPPING_FILE = "investment_master_mapping.csv"
DB_FOLDER = "investment_data_warehouse"
_free_adapter = FreeDataAdapter()


def ensure_index_data_path() -> str:
    """Market-gate तपासणीसाठी RELIANCE.NS हा NIFTY-proxy म्हणून वापरला जातो —
    तो local नसेल तर आत्ता (on-demand) NSE वरून आणून ठेवतो."""
    _free_adapter._load("RELIANCE.NS")  # नसेल तर आपोआप fetch होईल
    return os.path.join(DB_FOLDER, "RELIANCE.NS_5year.csv")


@str_app.cache_data
def load_mapping() -> pd.DataFrame:
    if not os.path.exists(MAPPING_FILE):
        return pd.DataFrame()
    return pd.read_csv(MAPPING_FILE)


def render_global_sidebar() -> dict:
    """
    प्रत्येक page च्या सुरुवातीला हे call करा. हे sector/ticker/timeframe/broker
    निवडी दाखवतं, st.session_state मध्ये save करतं, आणि dict म्हणून परत देतं:
      {sector, ticker, timeframe, active_broker}
    """
    mapping_df = load_mapping()
    if mapping_df.empty:
        str_app.sidebar.error("❌ `investment_master_mapping.csv` सापडली नाही!")
        str_app.stop()

    str_app.sidebar.markdown("<h2 style='color:#3182ce; margin-top:0;'>⚙️ CONTROL PANEL</h2>", unsafe_allow_html=True)

    sectors = list(mapping_df['Micro_Sector'].unique())
    default_sector_idx = sectors.index(str_app.session_state.get("selected_sector", sectors[0])) if str_app.session_state.get("selected_sector") in sectors else 0
    selected_sector = str_app.sidebar.selectbox("🎯 मायक्रो-सेक्टर:", sectors, index=default_sector_idx)
    str_app.session_state["selected_sector"] = selected_sector

    filtered_tickers = mapping_df[mapping_df['Micro_Sector'] == selected_sector]['Ticker'].tolist()
    default_ticker_idx = filtered_tickers.index(str_app.session_state["selected_ticker"]) if str_app.session_state.get("selected_ticker") in filtered_tickers else 0
    selected_ticker = str_app.sidebar.selectbox("⭐ कंपनी:", filtered_tickers, index=default_ticker_idx)
    str_app.session_state["selected_ticker"] = selected_ticker

    str_app.sidebar.markdown("---")
    broker_choice = str_app.sidebar.selectbox(
        "🏦 Broker (ऐच्छिक — live data):",
        list(AVAILABLE_BROKERS.keys()),
        format_func=lambda k: AVAILABLE_BROKERS[k][0],
        key="broker_choice",
    )
    active_broker = None
    if broker_choice != "free":
        broker_label = AVAILABLE_BROKERS[broker_choice][0]
        token = str_app.sidebar.text_input(f"{broker_label} Access Token:", type="password", key="broker_token")
        if token:
            try:
                candidate = get_broker_adapter(broker_choice, access_token=token)
                if candidate.is_connected():
                    active_broker = candidate
                    str_app.sidebar.success(f"✅ {candidate.display_name()} जोडलं गेलं")
                else:
                    str_app.sidebar.warning("Connect झालं नाही — free data वापरलं जाईल.")
            except Exception as e:
                str_app.sidebar.error(f"Connect अयशस्वी: {e}")
    else:
        str_app.sidebar.caption("Free NSE (delayed) data वापरलं जातंय.")
    str_app.sidebar.markdown("---")

    timeframe = str_app.sidebar.radio(
        "🕯️ टाइमफ्रेम:",
        ["75-Minute (इंट्रा-डे)", "Daily (दैनिक)", "Weekly (साप्ताहिक)", "Monthly (मासिक)"],
        key="timeframe",
    )

    return {
        "sector": selected_sector,
        "ticker": selected_ticker,
        "timeframe": timeframe,
        "active_broker": active_broker,
        "mapping_df": mapping_df,
    }


def render_disclaimer_banner():
    str_app.markdown(
        "<div style='background-color:#2d1b1b; border-left:4px solid #e53e3e; padding:10px 15px; "
        "border-radius:4px; font-size:12.5px; color:#fbb6b6; margin-bottom:10px;'>"
        "⚠️ <b>Disclaimer:</b> हे टूल केवळ शैक्षणिक/माहितीच्या उद्देशाने ऐतिहासिक डेटा-पॅटर्न विश्लेषण दाखवतं. "
        "हा SEBI-नोंदणीकृत गुंतवणूक सल्ला नाही आणि कुठलाही मजकूर खरेदी/विक्रीची शिफारस समजू नये. "
        "गुंतवणुकीचे निर्णय घेण्यापूर्वी स्वतःचं संशोधन करा किंवा नोंदणीकृत सल्लागाराचा सल्ला घ्या."
        "</div>",
        unsafe_allow_html=True,
    )
