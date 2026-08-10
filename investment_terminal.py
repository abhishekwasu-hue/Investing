import os
import time
import streamlit as str_app
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import investment_technical as tech

DB_FOLDER = "investment_data_warehouse"
MAPPING_FILE = "investment_master_mapping.csv"

str_app.set_page_config(page_title="Alpha Quant Pro Terminal", layout="wide")
str_app.markdown("""
    <style>
        .main { background-color: #0b0e14; }
        div.stDownloadButton > button:first-child { background-color: #38a169; color: white; border-radius: 6px; font-weight: bold; width: 100%; height: 45px; box-shadow: 0 4px 6px rgba(56,161,105,0.2); }
        .stRadio > div { flex-direction: row; gap: 15px; }
        .metric-card { background-color: #131722; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39; color: white; text-align: center; }
        .score-box { background-color: #1a202c; padding: 10px; border-radius: 6px; text-align: center; border-left: 5px solid #ecc94b; }
    </style>
""", unsafe_allow_html=True)

str_app.title("🏆 ALPHA UNIVERSAL INVESTMENT TERMINAL (PRO)")
str_app.markdown("---")

str_app.sidebar.markdown("<h2 style='color:#3182ce; margin-top:0;'>⚙️ CONTROL PANEL</h2>", unsafe_allow_html=True)
if not os.path.exists(MAPPING_FILE):
    str_app.sidebar.error("❌ `investment_master_mapping.csv` फाईल सापडली नाही!")
    str_app.stop()

mapping_df = pd.read_csv(MAPPING_FILE)
selected_sector = str_app.sidebar.selectbox("🎯 कस्टम मायक्रो-सेक्टर निवडा:", list(mapping_df['Micro_Sector'].unique()))
filtered_tickers = mapping_df[mapping_df['Micro_Sector'] == selected_sector]['Ticker'].tolist()
selected_ticker = str_app.sidebar.selectbox("⭐ कंपनी वॉचलिस्ट (Watchlist):", filtered_tickers)
timeframe = str_app.sidebar.radio("🕯️ चार्ट टाइमफ्रेम बदल:", ["75-Minute (इंट्रा-डे)", "Daily (दैनिक)", "Weekly (साप्ताहिक)", "Monthly (मासिक)"])

show_drawings = str_app.sidebar.toggle("📐 प्रगत SMC, FVG आणि ट्रेंडलाईन्स दाखवा", value=True)
live_toggle = str_app.sidebar.toggle("🔄 १-सेकंद जिवंत टिक अपडेट", value=False)

# 📥 Fix: Permanent Sidebar Placement for Download Action Controls
str_app.sidebar.markdown("---")
str_app.sidebar.markdown("### 📥 EXECUTIVE REPORT")

chart_placeholder = str_app.empty()
file_path = os.path.join(DB_FOLDER, f"{selected_ticker}_5year.csv")
index_path = os.path.join(DB_FOLDER, "RELIANCE.NS_5year.csv")

df_raw = pd.read_csv(file_path)
df_raw['Date'] = pd.to_datetime(df_raw['Date'])
analysis = tech.run_advanced_technical_analysis(df_raw, timeframe, index_path)

if analysis["status"] == "SUCCESS":
    chart_data = analysis["chart_data"]
    quant_score = analysis["score"]
    regime_status = analysis["regime"]
    research_text = analysis["reason"]
    swing_highs = analysis["swing_highs"]
    swing_lows = analysis["swing_lows"]
    fvg_boxes = analysis["fvg_boxes"]
    market_gate = analysis["market_gate"]
    delivery_15d = analysis["delivery_15d"]
    wyckoff_phase = analysis["wyckoff_phase"]
else:
    str_app.error("❌ क्वांट डेटा लोड करताना तांत्रिक चूक झाली.")
    str_app.stop()

complete_report_html = f"""
<html>
<body style='font-family: Arial, sans-serif; padding: 35px; color: #2d3748;'>
    <div style='max-width: 800px; margin: 0 auto; border: 1px solid #cbd5e0; padding: 40px; border-radius: 8px;'>
        <h2 style='color:#1a365d; text-align:center;'>🏆 ALPHA QUANT REAL-TIME EXECUTIVE REPORT</h2>
        <p style='text-align:center;'><b>दिनांक:</b> {datetime.now().strftime('%d-%b-%Y')} | <b>टर्मिनल विझ्युलायझेशन मोड:</b> {timeframe}</p>
        <hr style='border: 1px solid #3182ce;'>
        <p><b>Master Quant Score:</b> {quant_score}/100 | <b>Market Gate Context:</b> {market_gate}</p>
        <p><b>संशोधन मीमांसा (Research Framework):</b> {research_text}</p>
    </div>
</body>
</html>
"""
str_app.sidebar.download_button(label="📥 डाऊनलोड रिसर्च रिपोर्ट", data=complete_report_html, file_name=f"Alpha_Pro_Report_{selected_ticker}.html", mime="text/html")

with chart_placeholder.container():
    latest_close = chart_data['Close'].iloc[-1]
    if live_toggle:
        latest_close += np.random.uniform(-1.5, 1.5)
        chart_data.loc[chart_data.index[-1], 'Close'] = latest_close
        
    c1, c2, c3, c4 = str_app.columns(4)
    with c1: str_app.markdown(f"<div class='metric-card'>💵 <b>LIVE LTP:</b><br><span style='font-size:20px; color:#26a69a; font-weight:bold;'>Rs.{latest_close:.2f}</span></div>", unsafe_allow_html=True)
    with c2: str_app.markdown(f"<div class='metric-card'>📥 <b>15-DAY DELIVERY AVG:</b><br><span style='font-size:20px; color:#3182ce; font-weight:bold;'>{delivery_15d:.1f}%</span></div>", unsafe_allow_html=True)
    with c3: str_app.markdown(f"<div class='metric-card'>🌍 <b>NIFTY 500 GATE:</b><br><span style='font-size:20px; color:#38a169; font-weight:bold;'>{market_gate}</span></div>", unsafe_allow_html=True)
    with c4: str_app.markdown(f"<div class='score-box'>🏆 <b>QUANT SCORE:</b><br><span style='font-size:20px; color:#ecc94b; font-weight:bold;'>{quant_score}/100</span></div>", unsafe_allow_html=True)

    str_app.markdown("<br>", unsafe_allow_html=True)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.04)

    fig.add_trace(go.Candlestick(x=chart_data['Date'], open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], name=selected_ticker, increasing_line_color='#26a69a', decreasing_line_color='#ef5350'), row=1, col=1)
    fig.add_trace(go.Scatter(x=chart_data['Date'], y=chart_data['EMA_50'], line=dict(color='rgba(49, 130, 206, 0.6)', width=1.5), name="EMA 50 Support"), row=1, col=1)

    if show_drawings:
        for box in fvg_boxes[:3]:
            fig.add_shape(type="rect", x0=chart_data['Date'].iloc[0], x1=chart_data['Date'].iloc[-1], y0=box["bottom"], y1=box["top"], fillcolor="rgba(38, 166, 154, 0.04)", line=dict(width=0), row=1, col=1)
        if len(swing_highs) > 0:
            fig.add_hline(y=swing_highs[-1], line_color="#ef5350", line_width=1.5, line_dash="dash", annotation_text=f"🚨 SUPPLY (CHoCH) - Rs.{swing_highs[-1]:.1f}", annotation_position="top left", row=1, col=1)
        if len(swing_lows) > 0:
            fig.add_hline(y=swing_lows[-1], line_color="#26a69a", line_width=1.5, line_dash="dash", annotation_text=f"🛡️ DEMAND (BOS) - Rs.{swing_lows[-1]:.1f}", annotation_position="bottom left", row=1, col=1)

    fig.add_trace(go.Scatter(x=chart_data['Date'], y=chart_data['RSI'], line=dict(color='#805ad5', width=1.5), name="Momentum"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(239, 83, 80, 0.4)", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(38, 166, 154, 0.4)", row=2, col=1)

    # 🔴 Fix: Advanced Plotly Zoom and Axis Constraint Configuration Parameters Locked
    fig.update_layout(template="plotly_white", xaxis_rangeslider_visible=False, height=580, margin=dict(l=20, r=75, t=10, b=10), yaxis=dict(side="right", title="Price INR", fixedrange=False), yaxis2=dict(side="right", title="RSI Scale"), dragmode="pan")
    str_app.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

    str_app.markdown("---")
    str_app.info(f"📊 **क्वांट विश्लेषण स्टेटस ({timeframe}):** {regime_status} | Wyckoff Node Context: {wyckoff_phase}")
    str_app.markdown(f"<div style='background-color:#edf2f7; padding:15px; border-radius:6px; border-left:5px solid #3182ce; font-size:14px; color:#2d3748;'><b>संशोधन मीमांसा:</b><br>{research_text}</div>", unsafe_allow_html=True)

if live_toggle:
    time.sleep(1)
    str_app.rerun()
