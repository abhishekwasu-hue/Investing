import os
import pandas as pd
import yfinance as yf

# NSDL सेक्टर-वार FPI flow साठी कुठलंही मोफत रिअल-टाइम API उपलब्ध नाही.
# त्यांचे fortnightly रिपोर्ट्स इथे PDF/Excel स्वरूपात असतात:
#   https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx
# त्यामुळे fake numbers दाखवण्याऐवजी, हा फाईल-बेस्ड मॅन्युअल-अपडेट पॅटर्न वापरतो:
# वरील रिपोर्टमधून सेक्टर-वार आकडे काढून खालील CSV मध्ये स्वतः अपडेट करा.
FPI_FLOWS_FILE = "fpi_flows_manual.csv"  # columns: Sector,Flow_Cr


def fetch_nsdl_fpi_flow_report():
    """
    Returns (flows_dict, is_real_data).
    If fpi_flows_manual.csv is missing, returns an empty dict + False flag
    instead of fabricated numbers — the UI should show 'data not available'.
    """
    if os.path.exists(FPI_FLOWS_FILE):
        try:
            df = pd.read_csv(FPI_FLOWS_FILE)
            flows = dict(zip(df["Sector"], df["Flow_Cr"]))
            print(f"[MACRO ENGINE] Loaded {len(flows)} sector FPI flows from {FPI_FLOWS_FILE}.")
            return flows, True
        except Exception as e:
            print(f"[MACRO ENGINE] Could not parse {FPI_FLOWS_FILE}: {e}")

    print("[MACRO ENGINE] No FPI flow data file found — returning empty (no fake data).")
    return {}, False


def fetch_global_commodity_trends():
    """
    REAL crude oil (WTI futures, CL=F) and US Dollar Index (DX-Y.NYB),
    fetched live from Yahoo Finance instead of hardcoded values.
    """
    crude_oil_price = None
    dollar_index_dxy = None

    try:
        crude_hist = yf.Ticker("CL=F").history(period="5d")
        if not crude_hist.empty:
            crude_oil_price = float(crude_hist["Close"].dropna().iloc[-1])
    except Exception as e:
        print(f"[MACRO ENGINE] Crude oil fetch failed: {e}")

    try:
        dxy_hist = yf.Ticker("DX-Y.NYB").history(period="5d")
        if not dxy_hist.empty:
            dollar_index_dxy = float(dxy_hist["Close"].dropna().iloc[-1])
    except Exception as e:
        print(f"[MACRO ENGINE] DXY fetch failed: {e}")

    macro_narrative = ""
    if crude_oil_price is not None and crude_oil_price > 75.0:
        macro_narrative += (
            "• *Crude Oil Alert:* क्रूड ऑईलचे भाव वाढल्यामुळे देशांतर्गत इथेनॉलची मागणी "
            "वाढू शकते. साखरेपासून इथेनॉल बनत असल्याने Sugar Sector ला याचा फायदा होऊ शकतो.\n"
        )
    if dollar_index_dxy is not None and dollar_index_dxy < 103.0:
        macro_narrative += (
            "• *DXY Dollar Index:* डॉलर इंडेक्स तुलनेने कमजोर असल्यास जागतिक गुंतवणूकदार "
            "(FPI) भारतीय इक्विटी मार्केटकडे वळण्याची शक्यता वाढते."
        )
    if crude_oil_price is None or dollar_index_dxy is None:
        macro_narrative += "\n⚠️ काही live मॅक्रो डेटा मिळाला नाही (नेटवर्क किंवा सोर्स इश्यू)."

    return crude_oil_price, dollar_index_dxy, macro_narrative
