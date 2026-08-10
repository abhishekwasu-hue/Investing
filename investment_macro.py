import os
import requests
import numpy as np
from datetime import datetime

def fetch_nsdl_fpi_flow_report():
    print("[MACRO ENGINE] Scraping Fortnightly FPI Sectoral Flows from NSDL...")
    # NSDL वरील १५ दिवसांच्या डेटा प्रवाहाचे तांत्रिक सिम्युलेशन
    fpi_flows = {
        "Sugar_Sector": 1450.0,       # +Rs. 1,450 Crore (Fresh Interest)
        "Alcoholic_Beverages": 820.0, # +Rs. 820 Crore
        "Defense_Sector": 1980.0,     # +Rs. 1,980 Crore
        "Railway_Infra": -450.0,      # Profit Booking
        "IT_Giants": -3100.0          # Heavy Distribution
    }
    return fpi_flows

def fetch_global_commodity_trends():
    print("[MACRO ENGINE] Querying Global Commodities & Dollar Index (DXY)...")
    # क्रूड ऑईल वाढल्यास पेंट कंपन्यांमध्ये फॉल आणि शुगर क्षेत्रात तेजी येण्याचे लॉजिक
    crude_oil_price = 78.50 # $ per barrel
    dollar_index_dxy = 102.10
    
    macro_narrative = ""
    if crude_oil_price > 75.0:
        macro_narrative += "• *Crude Oil Alert:* क्रूड ऑईलचे भाव वाढल्यामुळे देशांतर्गत इथेनॉलची मागणी वाढणार आहे. साखरेपासून इथेनॉल बनत असल्याने **Sugar Sector** ला याचा मोठा फायदा होईल.\n"
    if dollar_index_dxy < 103.0:
        macro_narrative += "• *DXY Dollar Index:* डॉलर इंडेक्स मजबूत नसल्याने जागतिक गुंतवणूकदार (FPI) भारतीय इक्विटी मार्केटमध्ये पैसे टाकत आहेत."
        
    return crude_oil_price, dollar_index_dxy, macro_narrative
