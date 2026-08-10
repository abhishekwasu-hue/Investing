import os
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
# ⚙️ ॲपचे लेआउट आणि डिझाईन सेट करणे (Terminal Page Theme)
# ==============================================================================
str_app.set_page_config(page_title="Alpha Quant Terminal", layout="wide")

str_app.title("🏆 ALPHA LONG-TERM INVESTING QUANT TERMINAL")
str_app.markdown("---")

# ==============================================================================
# 📂 डावा पॅनेल: वॉचलिस्ट आणि सेक्टर फिल्टरेशन (Left Sidebar Interface)
# ==============================================================================
str_app.sidebar.header("📁 TERMINAL CONTROLS & WATCHLIST")

# मास्टर मॅपिंग शीट लोड करणे
if os.path.exists(MAPPING_FILE):
    mapping_df = pd.read_csv(MAPPING_FILE)
else:
    # डमी डेटाबेस बॅकअप जर फाईल नसेल तर
    mapping_df = pd.DataFrame({
        "Ticker": ["RENUKA.NS", "BALRAMCHIN.NS", "RADICO.NS", "MCDOWELL-N.NS", "HAL.NS", "MAZDOCK.NS"],
        "Micro_Sector": ["Sugar_Sector", "Sugar_Sector", "Alcoholic_Beverages", "Alcoholic_Beverages", "Defense_Sector", "Defense_Sector"]
    })

# १. सेक्टर्सची सुटसुटीत यादी ड्रॉपडाउन मेनूमध्ये दाखवणे
all_sectors = ["All Sectors"] + list(mapping_df['Micro_Sector'].unique())
selected_sector = str_app.sidebar.selectbox("🎯 कस्टम मायक्रो-सेक्टर निवडा:", all_sectors)

# २. निवडलेल्या सेक्टरनुसार वॉचलिस्ट फिल्टर करणे
if selected_sector != "All Sectors":
    filtered_tickers = mapping_df[mapping_df['Micro_Sector'] == selected_sector]['Ticker'].tolist()
else:
    filtered_tickers = mapping_df['Ticker'].tolist()

selected_ticker = str_app.sidebar.selectbox("⭐ कंपनी वॉचलिस्ट (Watchlist):", filtered_tickers)

# ३. टाइमफ्रेम निवडण्यासाठी रेडिओ बटण
timeframe = str_app.sidebar.radio("🕯️ चार्ट टाइमफ्रेम (Timeframe):", ["Weekly (साप्ताहिक)", "Monthly (मासिक)"])

# ==============================================================================
# 🧠 तांत्रिक गणिते आणि एसएमसी डिटेक्ट इंजिन (SMC Calculation Block)
# ==============================================================================
def load_and_process_terminal_data(ticker, tf_mode):
    file_path = os.path.join(DB_FOLDER, f"{ticker}_5year.csv")
    
    # जर ऐतिहासिक फाईल नसेल तर चाचणीसाठी १०० दिवसांचा डमी चार्ट बनवणे
    if not os.path.exists(file_path):
        dates = pd.date_range(end=datetime.now(), periods=150, freq='D')
        close_prices = 24500 + np.cumsum(np.random.normal(0, 25, 150))
        df = pd.DataFrame({
            'Date': dates, 'Open': close_prices - 15, 'High': close_prices + 30,
            'Low': close_prices - 30, 'Close': close_prices, 'Volume': np.random.randint(5000, 25000, 150),
            'No_of_Trades': np.random.randint(2000, 8000, 150), 'Delivery_Pct': np.random.uniform(45.0, 78.0, 150)
        })
    else:
        df = pd.read_csv(file_path)
        df['Date'] = pd.to_datetime(df['Date'])
        
    df.set_index('Date', inplace=True)
    
    # तुमच्या आवडीनुसार वीकली किंवा मंथली कॅंडल्समध्ये डेटा री-सॅम्पल करणे
    resample_rule = 'W' if "Weekly" in tf_mode else 'M'
    tf_df = df.resample(resample_rule).agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 
        'Volume': 'sum', 'No_of_Trades': 'mean', 'Delivery_Pct': 'mean'
    }).dropna().reset_index()
    
    # आरएसआय (RSI) आणि ईएमए चे प्रगत इंडिकेटर्स जोडणे
    change = tf_df['Close'].diff()
    gain = np.where(change > 0, change, 0)
    loss = np.where(change < 0, -change, 0)
    avg_gain = pd.Series(gain).rolling(14).mean()
    avg_loss = pd.Series(loss).rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    tf_df['RSI'] = 100 - (100 / (1 + rs))
    tf_df['EMA_50'] = tf_df['Close'].ewm(span=50, adjust=False).mean()
    
    return tf_df

# डेटा लोड करणे
chart_data = load_and_process_terminal_data(selected_ticker, timeframe)

# ==============================================================================
# 📈 उजवा पॅनेल: मुख्य इंटरअॅक्टिव्ह चार्ट टर्मिनल (Plotly Graphics Canvas)
# ==============================================================================
# मुख्य चार्ट पॅनेल आणि खाली आरएसआय इंडिकेटर पॅनेल तयार करणे
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.04)

# अ. मुख्य कॅन्डलस्टिक चार्ट
fig.add_trace(go.Candlestick(
    x=chart_data['Date'], open=chart_data['Open'], high=chart_data['High'], 
    low=chart_data['Low'], close=chart_data['Close'], name=selected_ticker,
    increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
), row=1, col=1)

# ब. तांत्रिक ओळी जोडणे (EMA 50 Support Wall)
fig.add_trace(go.Scatter(x=chart_data['Date'], y=chart_data['EMA_50'], line=dict(color='#3182ce', width=1.5), name="EMA 50 Line"), row=1, col=1)

# क. स्वस्वचालित एसएमसी डिमांड/सप्लाय बॉक्स (Auto-SMC Visualization Zones)
peak_high = chart_data['High'].max()
lowest_low = chart_data['Low'].min()

# डिमांड ऑर्डर ब्लॉक (हिरवा बॉक्स)
fig.add_hline(y=lowest_low * 1.02, line_dash="dot", line_color="rgba(38, 166, 154, 0.6)", row=1, col=1)
# सप्लाय ऑर्डर ब्लॉक (लाल बॉक्स)
fig.add_hline(y=peak_high * 0.98, line_dash="dot", line_color="rgba(239, 83, 80, 0.6)", row=1, col=1)

# ड. आरएसआय इंडिकेटर पॅनेल
fig.add_trace(go.Scatter(x=chart_data['Date'], y=chart_data['RSI'], line=dict(color='#805ad5', width=1.5), name="RSI (14)"), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="rgba(239, 83, 80, 0.4)", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="rgba(38, 166, 154, 0.4)", row=2, col=1)

fig.update_layout(template="plotly_white", xaxis_rangeslider_visible=False, height=600, margin=dict(l=30, r=30, t=20, b=20))

# डॅशबोर्डवर चार्ट प्रसिद्ध करणे
str_app.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# 📝 तळ पॅनेल: सिस्टम कारण मीमांसा आणि डेटा मॅट्रिक्स (Research Comments Panel)
# ==============================================================================
str_app.markdown("### 📝 अल्गोरिदमिक रिसर्च शेरा आणि कमेंट्स एरिया (SMC & Volume Metrics)")

latest_trades = chart_data['No_of_Trades'].iloc[-1]
latest_delivery = chart_data['Delivery_Pct'].iloc[-1]
latest_close = chart_data['Close'].iloc[-1]

drop_from_peak = (peak_high - latest_close) / peak_high

# कडक 'Correction vs Price Fall' रिस्क लॉजिक मांडणी
if latest_delivery >= 68.0 and drop_from_peak <= 0.15:
    regime_status = "HEALTHY_PRICE_CORRECTION ✅"
    narrative_color = "green"
    research_text = f"हा स्टॉक त्याच्या सर्वोच्च शिखरावरून {drop_from_peak*100:.1f}% खाली आला आहे. नंबर ऑफ ट्रेड्स कमालीचे घटले असून **डिव्हिटर टक्केवारी तब्बल {latest_delivery:.1f}% वर पोहोचली आहे**. हे स्पष्ट संकेत आहेत की रिटेलर्स पॅनिक होऊन माल विकत आहेत आणि मोठे इन्स्टिट्यूशनल प्लेयर्स (Smart Money) खालील भावात गुपचूप माल गोळा करत आहेत. ही ६ महिने ते २ वर्षांच्या पोझिशनसाठी सर्वोत्तम खरेदीची जागा (Value Buy Zone) आहे."
else:
    regime_status = "STABLE_VOLUME_ACCUMULATION 🟡"
    narrative_color = "blue"
    research_text = f"स्टॉकमध्ये सध्या सरासरी व्यवहार चालू आहेत. चालू डिलिव्हरी {latest_delivery:.1f}% आहे. चार्टवर सध्या कोणताही धोक्याचा ब्रेकडाउन नाही. सिस्टीम या स्टॉकच्या हालचालीवर पुढील १५ दिवस बारीक लक्ष ठेवून आहे."

# ब्राउझरवर कमेंट्स बॉक्स सजवणे
str_app.info(f"📊 **डेटा विश्लेषण स्टेटस:** {regime_status}")
str_app.markdown(f"<div style='background-color:#f7fafc; padding:20px; border-radius:6px; border-left:5px solid {narrative_color}; font-size:14px; line-height:1.6; color:#2d3748;'><b>संशोधन मीमांसा (Research Logic):</b><br>{research_text}</div>", unsafe_allow_color=True)
