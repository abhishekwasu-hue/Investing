import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==============================================================================
# 🧠 LAYER 1: MATHEMATICAL SMC & TECHNICAL INDICATORS ENGINE
# ==============================================================================
def calculate_indicators_and_smc(df):
    """SMC स्ट्रक्चर (BOS, CHoCH, Order Blocks) आणि इंडिकेटर्सचे अचूक गणित करणे."""
    # A. पारंपारिक इंडिकेटर्स (RSI & Moving Averages)
    change = df['Close'].diff()
    gain = change.mask(change < 0, 0)
    loss = -change.mask(change > 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    # B. स्विंग पिव्होट्स शोधणे (SMC साठी मागील ५ कॅंडल्सचा हाय/लो तपासणे)
    df['Pivot_High'] = df['High'].rolling(window=5, center=True).max()
    df['Pivot_Low'] = df['Low'].rolling(window=5, center=True).min()
    
    # C. BOS / CHoCH आणि Order Blocks चे लॉजिक ट्रॅकर्स
    df['BOS_Line'] = np.nan
    df['CHoCH_Line'] = np.nan
    df['Order_Block_Demand'] = np.nan
    df['Order_Block_Supply'] = np.nan
    
    # सोप्या आणि वेगवान चाचणीसाठी महत्त्वाच्या स्विंग लेव्हल्स निश्चित करणे
    for i in range(5, len(df)):
        # जर किंमत मागील महत्त्वाच्या हायच्या वर क्लोज झाली तर: Break of Structure (BOS)
        if df['Close'].iloc[i] > df['High'].iloc[i-5:i].max():
            df.loc[df.index[i], 'BOS_Line'] = df['High'].iloc[i-5:i].max()
            df.loc[df.index[i], 'Order_Block_Demand'] = df['Low'].iloc[i-5:i].min() # डिमांड झोन
            
        # जर मार्केटने पूर्ण कल बदलला तर: Change of Character (CHoCH)
        if df['Close'].iloc[i] < df['Low'].iloc[i-5:i].min():
            df.loc[df.index[i], 'CHoCH_Line'] = df['Low'].iloc[i-5:i].min()
            df.loc[df.index[i], 'Order_Block_Supply'] = df['High'].iloc[i-5:i].max() # सप्लाय झोन
            
    return df

# ==============================================================================
# 📊 LAYER 2: INTERACTIVE INTERFACES GENERATOR (PLOTLY DASHBOARD)
# ==============================================================================
def generate_interactive_quant_dashboard():
    csv_file = "nifty_3year_historical.csv"
    
    # १. जर लोकल फाईल नसेल, तर मॅन्युअल टेस्टिंगसाठी ५० दिवसांचा डमी डेटा तयार करणे
    if not os.path.exists(csv_file):
        print(f"[INFO] '{csv_file}' फाईल सापडली नाही. चाचणीसाठी डमी डेटा तयार करत आहे...")
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        close_prices = 24500 + np.cumsum(np.random.normal(0, 20, 100))
        df = pd.DataFrame({
            'Date': dates, 'Open': close_prices - 10, 'High': close_prices + 20,
            'Low': close_prices - 20, 'Close': close_prices, 'Volume': np.random.randint(1000, 5000, 100)
        })
    else:
        df = pd.read_csv(csv_file)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.tail(100) # चार्ट स्पष्ट दिसण्यासाठी आपण मागील १०० कॅंडल्सचा वापर करू
        
    # २. इंडिकेटर्स आणि एसएमसी लेव्हल्सचे कॅल्क्युलेशन करणे
    df = calculate_indicators_and_smc(df)
    
    # ३. सबप्लॉट्स तयार करणे (वर मुख्य चार्ट, खाली आरएसआय इंडिकेटर)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        row_heights=[0.75, 0.25], vertical_spacing=0.05)
    
    # 🕯️ अ. मुख्य कॅन्डलस्टिक चार्ट (Main Candlestick Panel)
    fig.add_trace(go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="NIFTY 50", increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    ), row=1, col=1)
    
    # 📉 ब. इंडिकेटर ओळी जोडणे (EMA 20)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_20'], line=dict(color='#3182ce', width=1.5), name="EMA 20"), row=1, col=1)
    
    # 🧱 क. एसएमसी लेव्हल्स ड्रॉ करणे (BOS, CHoCH, Order Blocks)
    # डिमांड झोन (Demand Order Block) - हिरवा पारदर्शक बॉक्स
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Order_Block_Demand'], mode='lines',
        line=dict(color='rgba(38, 166, 154, 0.4)', width=1, dash='dot'), name="SMC Demand Zone"
    ), row=1, col=1)
    
    # सप्लाय झोन (Supply Order Block) - लाल पारदर्शक बॉक्स
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Order_Block_Supply'], mode='lines',
        line=dict(color='rgba(239, 83, 80, 0.4)', width=1, dash='dot'), name="SMC Supply Zone"
    ), row=1, col=1)

    # 🚀 ड. ट्रेड एक्झिक्युशन कमेंट्स आणि बाण (Trade Annotation Markers)
    # बॅकटेस्टिंग सोपे करण्यासाठी आपण चार्टच्या मध्यभागी एक डमी ट्रेड एक्झिक्युशन पॉईंट ड्रॉ करूया
    trade_index = len(df) // 2
    trade_date = df['Date'].iloc[trade_index]
    trade_price = df['Close'].iloc[trade_index]
    
    fig.add_annotation(
        x=trade_date, y=trade_price, text="🚀 ALGO ENTRY<br>६५ Qty NRML<br>ATM+4 Short Deployed",
        showarrow=True, arrowhead=2, arrowcolor='#2b6cb0', bgcolor='rgba(43, 108, 176, 0.1)',
        bordercolor='#2b6cb0', borderwidth=1, row=1, col=1
    )
    
    # 📊 इ. आरएसआय इंडिकेटर पॅनेल (RSI Subplot)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], line=dict(color='#805ad5', width=1.5), name="RSI (14)"), row=2, col=1)
    # आरएसआय ओव्हरबॉट/ओव्हरसोल्ड रेषा (70 / 30 Boundaries)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(239, 83, 80, 0.5)", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(38, 166, 154, 0.5)", row=2, col=1)
    
    # ४. डॅशबोर्डचे लेआउट आणि बटणे सजवणे (Styling Terminal Layout)
    fig.update_layout(
        title="🏆 NIFTY MULTI-ACCOUNT SWING QUANT TERMINAL DIAGRAM",
        template="plotly_white",
        xaxis_rangeslider_visible=False,
        height=750,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    # ५. स्वतंत्र लोकल HTML फाईल सेव्ह करून ब्राउझरमध्ये उघडणे
    output_filename = "nifty_SMC_dashboard.html"
    fig.write_html(output_filename)
    print(f"[🏁 DASHBOARD COMPLETE] Your interactive terminal chart has been saved as '{output_filename}'.")
    print("तुम्ही ही फाईल तुमच्या कॉम्प्युटरवर कोणत्याही इंटरनेट ब्राउझरमध्ये उघडून पूर्ण सुबक आणि रंगीत आलेख पाहू शकता!")

if __name__ == "__main__":
    generate_interactive_quant_dashboard()
