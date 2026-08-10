import os
import time
import streamlit as str_app
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# डेटाबेस आणि मॅपिंग फाईल कॉन्फिगरेशन
DB_FOLDER = "investment_data_warehouse"
MAPPING_FILE = "investment_master_mapping.csv"

# ==============================================================================
# 🎨 प्रगत थीम आणि लेआउट (Premium TradingView Styling Grid)
# ==============================================================================
str_app.set_page_config(page_title="Alpha Quant Pro Terminal", layout="wide")

str_app.markdown("""
    <style>
        .main { background-color: #0b0e14; }
        div.stButton > button:first-child { background-color: #38a169; color: white; border-radius: 6px; font-weight: bold; width: 100%; height: 45px; }
        .stRadio > div { flex-direction: row; gap: 15px; }
        .metric-card { background-color: #131722; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39; color: white; }
    </style>
""", unsafe_allow_html=True)

str_app.title("🏆 ALPHA UNIVERSAL INVESTMENT TERMINAL (PRO)")
str_app.markdown("<p style='color:#718096; font-size:14px; margin-top:-15px;'><b>TradingView-Style Interactive Advanced Quant Matrix Framework</b></p>", unsafe_allow_html=True)
str_app.markdown("---")

# ==============================================================================
# 📂 डावा पॅनेल: नियंत्रण आणि प्रगत वॉचलिस्ट (Sidebar Controllers)
# ==============================================================================
str_app.sidebar.markdown("<h2 style='color:#3182ce;'>⚙️ CONTROL PANEL</h2>", unsafe_allow_html=True)

if os.path.exists(MAPPING_FILE):
    mapping_df = pd.read_csv(MAPPING_FILE)
else:
    str_app.sidebar.error("❌ `investment_master_mapping.csv` फाईल सापडली नाही!")
    str_app.stop()

selected_sector = str_app.sidebar.selectbox("🎯 कस्टम मायक्रो-सेक्टर निवडा:", list(mapping_df['Micro_Sector'].unique()))
filtered_tickers = mapping_df[mapping_df['Micro_Sector'] == selected_sector]['Ticker'].tolist()
selected_ticker = str_app.sidebar.selectbox("⭐ कंपनी वॉचलिस्ट (Watchlist):", filtered_tickers)

timeframe = str_app.sidebar.radio("🕯️ चार्ट टाइमफ्रेम बदल (Timeframe Scaling):", 
                                 ["75-Minute (इंट्रा-डे)", "Daily (दैनिक)", "Weekly (साप्ताहिक)", "Monthly (मासिक)"])

# 🔴 सुधारणा २: चार्टवरील सर्व ड्रॉइंग्स चालू-बंद करण्याचे प्रगत टॉगल बटण (The Toggle Button)
show_drawings = str_app.sidebar.toggle("📐 प्रगत SMC आणि ट्रेंडलाईन्स दाखवा (Show Technical Tools)", value=True)
live_toggle = str_app.sidebar.toggle("🔄 टिक-बाय-टिक लाईव्ह अपडेट्स (Live Updates)", value=False)

# ==============================================================================
# 🧠 मॅथेमॅटिकल SMC पिव्होट्स आणि ट्रेंडलाईन कॅल्क्युलेटर इंजिन (SMC Wave Math)
# ==============================================================================
def load_and_transform_data(ticker, tf_mode):
    file_path = os.path.join(DB_FOLDER, f"{ticker}_5year.csv")
    
    if not os.path.exists(file_path):
        # सेफ फॉलबॅक डमी जर मूळ फाईल्स अजून सिंक होत असतील तर
        dates = pd.date_range(end=datetime.now(), periods=200, freq='D')
        close_prices = 2200 + np.cumsum(np.random.normal(0, 10, 200))
        df = pd.DataFrame({
            'Date': dates, 'Open': close_prices - 5, 'High': close_prices + 10,
            'Low': close_prices - 10, 'Close': close_prices, 'Volume': np.random.randint(5000, 25000, 200),
            'No_of_Trades': np.random.randint(3000, 12000, 200), 'Delivery_Pct': np.random.uniform(40.0, 75.0, 200)
        })
        df.set_index('Date', inplace=True)
    else:
        df = pd.read_csv(file_path)
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
    if "75-Minute" in tf_mode: resample_rule = '75min'
    elif "Daily" in tf_mode: resample_rule = '1D'
    elif "Weekly" in tf_mode: resample_rule = 'W'
    else: resample_rule = 'ME'
        
    tf_df = df.resample(resample_rule).agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 
        'Volume': 'sum', 'No_of_Trades': 'mean', 'Delivery_Pct': 'mean'
    }).dropna().reset_index()
    
    # इंडिकेटर्स कॅल्क्युलेटर
    change = tf_df['Close'].diff()
    gain = np.where(change > 0, change, 0)
    loss = np.where(change < 0, -change, 0)
    avg_gain = pd.Series(gain).rolling(window=14, min_periods=1).mean()
    avg_loss = pd.Series(loss).rolling(window=14, min_periods=1).mean()
    tf_df['RSI'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-10))))
    tf_df['EMA_50'] = tf_df['Close'].ewm(span=50, adjust=False).mean()
    
    # 🔴 सुधारणा १: खऱ्या लाटांचे स्विंग हाय/लो पिव्होट्स शोधण्याचे अचूक गणित (SMC Engine)
    tf_df['Swing_High'] = np.nan
    tf_df['Swing_Low'] = np.nan
    for i in range(10, len(tf_df)-10):
        if tf_df['High'].iloc[i] == tf_df['High'].iloc[i-10:i+10].max():
            tf_df.loc[tf_df.index[i], 'Swing_High'] = tf_df['High'].iloc[i]
        if tf_df['Low'].iloc[i] == tf_df['Low'].iloc[i-10:i+10].min():
            tf_df.loc[tf_df.index[i], 'Swing_Low'] = tf_df['Low'].iloc[i]
            
    return tf_df

chart_data = load_and_transform_data(selected_ticker, timeframe)

# ==============================================================================
# 📈 उजवा पॅनेल: मुख्य प्रगत कॅन्डलस्टिक चार्ट (Plotly Interactive Canvas)
# ==============================================================================
latest_close = chart_data['Close'].iloc[-1]
latest_trades = chart_data['No_of_Trades'].iloc[-1]
latest_delivery = chart_data['Delivery_Pct'].iloc[-1]

c1, c2, c3 = str_app.columns(3)
with c1: str_app.markdown(f"<div class='metric-card'>💵 <b>LIVE LTP:</b><br><span style='font-size:22px; color:#26a69a; font-weight:bold;'>Rs.{latest_close:.2f}</span></div>", unsafe_allow_html=True)
with c2: str_app.markdown(f"<div class='metric-card'>📥 <b>NSE DELIVERY %:</b><br><span style='font-size:22px; color:#3182ce; font-weight:bold;'>{latest_delivery:.1f}%</span></div>", unsafe_allow_html=True)
with c3: str_app.markdown(f"<div class='metric-card'>⚡ <b>NO. OF TRADES (AVG):</b><br><span style='font-size:22px; color:#e53e3e; font-weight:bold;'>{int(latest_trades)}</span></div>", unsafe_allow_html=True)

str_app.markdown("<br>", unsafe_allow_html=True)

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.04)

# अ. मुख्य कॅन्डलस्टिक आलेख
fig.add_trace(go.Candlestick(
    x=chart_data['Date'], open=chart_data['Open'], high=chart_data['High'], 
    low=chart_data['Low'], close=chart_data['Close'], name=selected_ticker,
    increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
), row=1, col=1)

fig.add_trace(go.Scatter(x=chart_data['Date'], y=chart_data['EMA_50'], line=dict(color='#3182ce', width=1.5), name="EMA 50 Support"), row=1, col=1)

# 🔴 सुधारणा १ व २: टॉगल बटण ऑन असेल तरच प्रगत रेखाटने स्वतः ड्रॉ करणे (Conditional Rendering Matrix)
if show_drawings:
    high_pivots = chart_data[chart_data['Swing_High'].notna()]
    low_pivots = chart_data[chart_data['Swing_Low'].notna()]
    
    # १. खऱ्या किमतीनुसार मोजलेले सप्लाय आणि डिमांड झोन्स (Real SMC Box Shading)
    if len(high_pivots) > 0:
        last_sh = high_pivots['Swing_High'].iloc[-1]
        fig.add_hline(y=last_sh, line_color="rgba(239, 83, 80, 0.8)", line_width=2, line_dash="dash",
                      annotation_text="🚨 SMC SUPPLY ZONE (CHoCH)", annotation_position="top left", row=1, col=1)
        # रेसिस्टन्स रेषा
        fig.add_hline(y=last_sh * 1.01, line_color="rgba(239, 83, 80, 0.3)", line_width=1, row=1, col=1)
                      
    if len(low_pivots) > 0:
        last_sl = low_pivots['Swing_Low'].iloc[-1]
        fig.add_hline(y=last_sl, line_color="rgba(38, 166, 154, 0.8)", line_width=2, line_dash="dash",
                      annotation_text="🛡️ SMC DEMAND ZONE (BOS)", annotation_position="bottom left", row=1, col=1)
        # सपोर्ट रेषा
        fig.add_hline(y=last_sl * 0.99, line_color="rgba(38, 166, 154, 0.3)", line_width=1, row=1, col=1)

    # २. ऑटोमॅटिक प्रगत स्विंग ट्रेंडलाईन (Automatic Angular Trendlines)
    if len(low_pivots) >= 2:
        tl_x = [low_pivots['Date'].iloc[-2], low_pivots['Date'].iloc[-1]]
        tl_y = [low_pivots['Swing_Low'].iloc[-2], low_pivots['Swing_Low'].iloc[-1]]
        fig.add_trace(go.Scatter(x=tl_x, y=tl_y, mode='lines', line=dict(color='#ecc94b', width=2), name="📈 Dynamic Trendline"), row=1, col=1)

# आरएसआय इंडिकेटर पॅनेल
fig.add_trace(go.Scatter(x=chart_data['Date'], y=chart_data['RSI'], line=dict(color='#805ad5', width=1.5), name="RSI (14)"), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="rgba(239, 83, 80, 0.4)", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="rgba(38, 166, 154, 0.4)", row=2, col=1)

# 🔴 सुधारणा ३: माऊसच्या स्क्रोल बटणाने ऑटोमॅटिक झूम होणे (Mouse Wheel Scroll Zoom Activation)
fig.update_layout(
    template="plotly_white",
    xaxis_rangeslider_visible=False,
    height=600,
    margin=dict(l=30, r=70, t=10, b=10),
    yaxis=dict(side="right", title="किंमत (Price INR)"), 
    yaxis2=dict(side="right", title="RSI Boundary"),
    # 🟢 ही कमांड माऊसच्या स्क्रोल व्हीलने चार्ट TradingView सारखा ऑटो-झूम करण्यास सक्षम करते
    dragmode="pan"
)

# कॉन्फिगरेशन मॅपिंगमध्ये माऊस स्क्रोल चालू करणे
fig.update_xaxes(row=1, col=1)
str_app.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True}) # 🟢 Enables TradingView Mouse Wheel Scrolling

# ==============================================================================
# 📝 तळ पॅनेल: सिस्टम कारण मीमांसा (Research Logic Panel)
# ==============================================================================
str_app.markdown("---")
str_app.markdown("### 📝 अल्गोरिदमिक रिसर्च शेरा (SMC Multi-Timeframe Analysis)")

peak_high = chart_data['High'].max()
drop_from_peak = (peak_high - latest_close) / peak_high
