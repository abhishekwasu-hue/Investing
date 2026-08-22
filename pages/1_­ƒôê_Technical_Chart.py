import streamlit as str_app
import pandas as pd
from datetime import datetime

import investment_technical as tech
import data_provider
from chart_builder import build_technical_chart
from app_state import render_global_sidebar, render_disclaimer_banner, DB_FOLDER
from auth import render_auth_gate
import os

str_app.set_page_config(page_title="Technical Chart | Alpha Quant Pro", layout="wide")
render_disclaimer_banner()
authenticator = render_auth_gate()
str_app.title("📈 Technical Chart & Structure Analysis")

state = render_global_sidebar()
ticker, timeframe, active_broker = state["ticker"], state["timeframe"], state["active_broker"]

# ---- डेटा लोड (broker-agnostic, आपोआप free data वर fallback) ----
try:
    to_date = datetime.now().date()
    from_date = to_date.replace(year=to_date.year - 5)
    df_raw = data_provider.get_ohlc_data(ticker, from_date, to_date, active_broker=active_broker)
except FileNotFoundError as e:
    str_app.error(f"❌ {e}")
    str_app.stop()

df_raw["Date"] = pd.to_datetime(df_raw["Date"])
index_path = os.path.join(DB_FOLDER, "RELIANCE.NS_5year.csv")

analysis = tech.run_advanced_technical_analysis(df_raw, timeframe, index_path)

if analysis["status"] != "SUCCESS":
    str_app.warning(f"⚠️ पुरेसा डेटा उपलब्ध नाही ({analysis.get('reason', 'unknown')}). एकदा `investment_database.py` चालवा.")
    str_app.stop()

chart_df = analysis["chart_data"]
quant_score = analysis["score"]
regime = analysis["regime"]
reason = analysis["reason"]
market_gate = analysis["market_gate"]
wyckoff_phase = analysis["wyckoff_phase"]

# ---- Score cards ----
c1, c2, c3, c4 = str_app.columns(4)
c1.metric("Quant Score", f"{quant_score}/100")
c2.metric("Regime (Pattern)", regime.replace("_", " "))
c3.metric("Market Gate (NIFTY proxy)", market_gate.replace("_", " "))
c4.metric("Wyckoff Phase", wyckoff_phase.split(" (")[0])

str_app.markdown(f"<div class='metric-card' style='text-align:left; margin-top:10px;'>{reason}</div>", unsafe_allow_html=True)

# ---- Candlestick chart with RSI subplot (shared builder — same chart used in PDF report) ----
fig = build_technical_chart(chart_df, analysis, ticker, timeframe)

str_app.caption(
    "🔵 निळे बॉक्स = Fair Value Gap (FVG) झोन | 🔴 लाल रेषा = Swing High | 🟢 हिरवी रेषा = Swing Low | "
    "हे सर्व ऐतिहासिक data-pattern मार्कर्स आहेत, ट्रेडिंग सिग्नल नाहीत."
)
