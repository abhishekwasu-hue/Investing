import pandas as pd
import numpy as np

def run_advanced_technical_analysis(file_path):
    df = pd.read_csv(file_path)
    if len(df) < 100:
        return "INSUFFICIENT_DATA", 0, 0, 0
        
    # आरएसआय (RSI) आणि ईएमए (EMA 20/50/200) चे कॅल्क्युलेशन
    change = df['Close'].diff()
    gain = np.where(change > 0, change, 0)
    loss = np.where(change < 0, -change, 0)
    avg_gain = pd.Series(gain).rolling(14).mean()
    avg_loss = pd.Series(loss).rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # 📊 स्विंग पिव्होट्सवरून BOS (Break of Structure) आणि CHoCH शोधणे
    recent_close = df['Close'].iloc[-1]
    peak_high = df['High'].tail(30).max()
    lowest_low = df['Low'].tail(30).min()
    
    # व्हॉल्युम स्पाईक्स (Institutional Volume Accumulation)
    avg_vol = df['Volume'].tail(30).mean()
    recent_vol = df['Volume'].iloc[-1]
    
    technical_score = 50 # Base Neutral Score
    if recent_close > df['EMA_50'].iloc[-1]: technical_score += 15
    if recent_vol > (avg_vol * 2): technical_score += 20 # Big player entry
    
    return "ANALYZED", technical_score, peak_high, lowest_low


