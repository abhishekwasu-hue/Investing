import streamlit as st
import pandas as pd
import numpy as np
import investment_technical as tech

# Streamlit Page Config
st.set_page_config(page_title="Alpha Universal Investment Terminal", layout="wide")

st.title("🏆 ALPHA UNIVERSAL INVESTMENT TERMINAL (PRO)")
st.caption("TradingView-Style Interactive Advanced Quant Matrix Framework with Sub-second Live Container")

# Live Stream Container
str_app = st.empty()

def render_metrics_safely(metrics):
    if metrics is None or metrics.empty:
        return
    
    latest_row = metrics.iloc[-1]
    live_ltp = latest_row.get('Close', 0.0)

    # SAFE CHECK FOR 15-DAY DELIVERY DMA (Prevents KeyError)
    if '15_Delivery_DMA' in metrics.columns and not pd.isna(latest_row['15_Delivery_DMA']):
        deliv_avg_val = f"{latest_row['15_Delivery_DMA']:.2f}%"
    elif 'Delivery_Pct' in metrics.columns and not pd.isna(latest_row['Delivery_Pct']):
        deliv_avg_val = f"{latest_row['Delivery_Pct']:.2f}%"
    else:
        deliv_avg_val = "N/A"

    # UI Render
    with str_app.container():
        st.markdown(f"""
            <div style='background-color:#1E222D; padding:10px; border-radius:8px; width:220px; text-align:center;'>
                <span style='color:#00E676; font-weight:bold;'>💵 LIVE LTP:</span><br>
                <span style='font-size:24px; color:#00E676; font-weight:bold;'>Rs. {live_ltp:.2f}</span>
            </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown(f"<div class='metric-card'>📊 <b>LATEST CLOSE:</b><br><span style='font-size:22px; color:#3182ce;'>Rs. {live_ltp:.2f}</span></div>", unsafe_allow_html=True)

        with c2:
            st.markdown(f"<div class='metric-card'>📦 <b>15-DAY DELIVERY AVG:</b><br><span style='font-size:22px; color:#3182ce;'>{deliv_avg_val}</span></div>", unsafe_allow_html=True)

        with c3:
            vol_val = f"{latest_row.get('Volume', 0):,}" if 'Volume' in metrics.columns else "N/A"
            st.markdown(f"<div class='metric-card'>📈 <b>VOLUME:</b><br><span style='font-size:22px; color:#3182ce;'>{vol_val}</span></div>", unsafe_allow_html=True)
