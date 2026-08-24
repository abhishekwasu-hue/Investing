import streamlit as str_app
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

import investment_technical as tech
import data_provider
from lightweight_chart import build_lightweight_chart_html
from app_state import render_global_sidebar, render_disclaimer_banner, DB_FOLDER, ensure_index_data_path
from auth import render_auth_gate
import os

str_app.set_page_config(page_title="Technical Chart | Alpha Quant Pro", layout="wide")
render_disclaimer_banner()
authenticator = render_auth_gate()
str_app.title("📈 Technical Chart & Structure Analysis")

state = render_global_sidebar()
ticker, timeframe, active_broker = state["ticker"], state["timeframe"], state["active_broker"]

# ---- डेटा लोड (broker-agnostic, आपोआप free data वर fallback, on-demand fetch) ----
is_intraday_tf = timeframe.startswith("75-Minute")

if is_intraday_tf:
    # ⚠️ 75-Minute साठी मिनिट-स्तरीय (intraday) डेटा लागतो — तो फक्त live
    # broker (उदा. Upstox) कडूनच मिळू शकतो. NSE/Yahoo (free source) कडे
    # फक्त daily डेटा असतो — तो resample करून intraday चार्ट बनवणं दिशाभूल
    # करणारं ठरेल, म्हणून तसं करत नाही.
    if active_broker is None or not active_broker.is_connected():
        str_app.warning(
            "⚠️ 75-Minute (इंट्रा-डे) चार्टसाठी मिनिट-स्तरीय डेटा लागतो, जो फक्त एखादा "
            "**live broker जोडलेला असेल तरच** (उदा. Upstox — sidebar मध्ये) मिळू शकतो. "
            "NSE/Yahoo Finance (free source) कडे फक्त daily (EOD) डेटा असतो. "
            "सध्या Daily/Weekly/Monthly पैकी एक निवडा, किंवा sidebar मधून broker जोडा."
        )
        str_app.stop()

    with str_app.spinner(f"{ticker} साठी intraday डेटा आणत आहे..."):
        to_date = datetime.now().date()
        from_date = to_date - pd.Timedelta(days=60)  # brokers सहसा intraday साठी मर्यादित इतिहासच देतात
        df_raw = data_provider.get_intraday_ohlc_data(ticker, from_date, to_date, active_broker=active_broker)

    if df_raw is None or df_raw.empty:
        str_app.error(
            f"❌ {active_broker.display_name()} कडून {ticker} साठी intraday डेटा मिळाला नाही "
            "(broker चा intraday history कमी दिवसांचाच असतो, किंवा API मध्ये तात्पुरती अडचण असू शकते)."
        )
        str_app.stop()
else:
    try:
        to_date = datetime.now().date()
        from_date = to_date.replace(year=to_date.year - 5)
        with str_app.spinner(f"{ticker} साठी डेटा तयार करत आहे (पहिल्यांदाच थोडा वेळ लागू शकतो)..."):
            df_raw = data_provider.get_ohlc_data(ticker, from_date, to_date, active_broker=active_broker)
    except FileNotFoundError as e:
        str_app.error(
            f"❌ {ticker} साठी कुठलाही data source (NSE/Yahoo Finance) डेटा देऊ शकला नाही. "
            "थोड्या वेळाने पुन्हा प्रयत्न करा, किंवा दुसरा ticker निवडून बघा."
        )
        str_app.stop()

if df_raw is None or df_raw.empty:
    str_app.error(f"❌ {ticker} साठी डेटा रिकामा आला.")
    str_app.stop()

df_raw["Date"] = pd.to_datetime(df_raw["Date"])
index_path = ensure_index_data_path()

analysis = tech.run_advanced_technical_analysis(df_raw, timeframe, index_path)

if analysis["status"] != "SUCCESS":
    str_app.warning(f"⚠️ पुरेसा डेटा उपलब्ध नाही ({analysis.get('reason', 'unknown')}). थोड्या दिवसांनी पुन्हा प्रयत्न करा.")
    str_app.stop()

chart_df = analysis["chart_data"]

if chart_df is None or chart_df.empty:
    str_app.warning("⚠️ Chart साठी पुरेसा डेटा नाही.")
    str_app.stop()

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

# ---- मुख्य चार्ट: TradingView Lightweight Charts (खरा TradingView look) ----
str_app.markdown("### 🕯️ Price Chart")
try:
    tv_html = build_lightweight_chart_html(chart_df, analysis, ticker, timeframe, height=520)
    components.html(tv_html, height=540, scrolling=False)
except Exception as e:
    str_app.error(f"⚠️ Chart रेंडर करताना अडचण आली: {e}")

str_app.caption(
    "🔴 लाल = Resistance | 🟢 हिरवा = Support | जितकी रेषा जाड/ठळक तितका तो level जास्त वेळा टच झालाय "
    "(जास्त probability) | 🟡 पिवळी रेषा = EMA 50 — हे सर्व ऐतिहासिक data-pattern मार्कर्स आहेत, ट्रेडिंग सिग्नल नाहीत."
)

# ---- Support/Resistance टेबल (chart खाली) — timeframe बदलला की आपोआप recalculate होतो ----
str_app.markdown("### 📐 Support & Resistance Levels")
sr_levels = tech.compute_support_resistance_levels(
    analysis.get("swing_highs", []), analysis.get("swing_lows", []), tolerance_pct=1.5
)

if sr_levels:
    sr_df = pd.DataFrame(sr_levels).rename(columns={
        "type": "Type", "price": "Price (₹)", "touch_count": "Touch Count", "strength": "Strength",
    })[["Type", "Price (₹)", "Touch Count", "Strength"]]

    def _highlight_strength(row):
        if row["Strength"] == "Strong":
            return ["background-color: #7a1f1f; font-weight: bold; color: white;" if row["Type"] == "Resistance"
                    else "background-color: #1f5c3a; font-weight: bold; color: white;"] * len(row)
        elif row["Strength"] == "Moderate":
            return ["background-color: #3a2323; color: #f7fafc;" if row["Type"] == "Resistance"
                    else "background-color: #1e3a2c; color: #f7fafc;"] * len(row)
        return [""] * len(row)

    styled_sr = sr_df.style.apply(_highlight_strength, axis=1)
    str_app.dataframe(styled_sr, use_container_width=True, hide_index=True)
    str_app.caption(
        f"एकूण {len(sr_levels)} levels ({timeframe} टाइमफ्रेमवर) — Strong (४+ touches) सगळ्यात ठळक "
        "रंगात, table वरती. टाइमफ्रेम बदलला की हे स्वयंचलितपणे पुन्हा calculate होतं."
    )
else:
    str_app.info("ℹ️ या टाइमफ्रेमवर पुरेसे swing points सापडले नाहीत — S/R levels दाखवता येत नाहीत.")

# ---- RSI (खाली, वेगळा छोटा चार्ट) ----
if "RSI" in chart_df.columns:
    str_app.markdown("### 📉 RSI (14)")
    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(x=chart_df["Date"], y=chart_df["RSI"], name="RSI", line=dict(color="#9f7aea", width=1.5)))
    rsi_fig.add_hline(y=70, line=dict(color="#e53e3e", width=0.5, dash="dash"))
    rsi_fig.add_hline(y=30, line=dict(color="#38a169", width=0.5, dash="dash"))
    rsi_fig.update_layout(
        height=200, template="plotly_dark", showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="#0b0e14", plot_bgcolor="#0b0e14",
    )
    str_app.plotly_chart(rsi_fig, use_container_width=True)
