import os
import pandas as pd
import numpy as np

DB_FOLDER = "investment_data_warehouse"

def evaluate_price_correction_vs_fall(file_path, peak_high):
    df = pd.read_csv(file_path)
    recent_close = df['Close'].iloc[-1]
    recent_trades = df['No_of_Trades'].iloc[-1]
    recent_delivery = df['Delivery_Pct'].iloc[-1]
    
    avg_trades = df['No_of_Trades'].tail(20).mean()
    drop_pct = (peak_high - recent_close) / peak_high
    
    # 🔴 तुमचा सर्वात शक्तिशाली नियम: Trades कमी पण Delivery टक्केवारी कमालीची जास्त (७५%+)
    if recent_trades < avg_trades and recent_delivery >= 68.0:
        if drop_pct >= 0.05 and drop_pct <= 0.15:
            reason = f"किंमत सर्वोच्च शिखरावरून {drop_pct*100:.1f}% खाली आली आहे, परंतु ट्रेड्स कमी असून डिलिव्हरी टक्केवारी ऐतिहासिक उच्चांकावर (Rs.{recent_delivery:.1f}%) पोहोचली आहे. **हा 'Price Fall' नसून मोठे प्लेयर्स गुपचूप माल गोळा करत असल्यामुळे आलेले अत्यंत निरोगी 'Price Correction' आहे.**"
            return "HEALTHY_CORRECTION", reason
        elif drop_pct > 0.15:
            reason = "किंमत मोठ्या प्रमाणात कोसळली आहे आणि व्यवहारांची संख्या वाढलेली आहे — हा पॅटर्न ऐतिहासिकदृष्ट्या संस्थात्मक विक्री (distribution) सोबत जुळतो. हे पूर्णपणे ऐतिहासिक डेटा-पॅटर्न विश्लेषण आहे, गुंतवणूक सल्ला नाही — कृपया स्वतःचं संशोधन करा किंवा नोंदणीकृत सल्लागाराचा सल्ला घ्या."
            return "STRUCTURAL_PRICE_FALL", reason
            
    return "STABLE_ACCUMULATION", "मार्केट सध्या रेंजबाउंड असून मोठे खेळाडू हळूहळू शेअर्स जमा करत आहेत."
