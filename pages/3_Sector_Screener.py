import os
import streamlit as str_app
import pandas as pd

import investment_technical as tech
import data_provider
from app_state import render_global_sidebar, render_disclaimer_banner, DB_FOLDER, ensure_index_data_path
from auth import render_auth_gate
import subscription

str_app.set_page_config(page_title="Sector Screener | Alpha Quant Pro", layout="wide")
render_disclaimer_banner()
authenticator = render_auth_gate()
username = str_app.session_state["username"]

state = render_global_sidebar()
sector, timeframe, mapping_df = state["sector"], state["timeframe"], state["mapping_df"]
active_broker = state["active_broker"]

if timeframe.startswith("75-Minute"):
    str_app.warning(
        "⚠️ Sector Screener सध्या 75-Minute (इंट्रा-डे) सपोर्ट करत नाही — एका sector मधल्या "
        "सगळ्या tickers साठी intraday डेटा आणणं खूप जास्त API calls लागतील. कृपया sidebar "
        "मधून Daily/Weekly/Monthly पैकी एक निवडा."
    )
    str_app.stop()

if not subscription.check_and_increment(username, "sector_screener"):
    str_app.error(
        f"⚠️ आजची Free-tier मर्यादा ({subscription.FREE_LIMITS['sector_screener']} screener runs/दिवस) संपली. "
        "उद्या पुन्हा प्रयत्न करा, किंवा Unlimited साठी sidebar वरून Upgrade to Pro करा."
    )
    str_app.stop()

str_app.title("🔍 Sector Screener")

sector_tickers = mapping_df[mapping_df["Micro_Sector"] == sector]["Ticker"].tolist()
index_path = ensure_index_data_path()

str_app.subheader(f"📂 {sector} — {len(sector_tickers)} tickers स्कॅन होत आहेत")
str_app.caption("ℹ️ ज्या tickers साठी local data नाही, ते आत्ता NSE वरून on-demand आणले जातील — पहिल्यांदा थोडा वेळ लागू शकतो.")

rows = []
progress = str_app.progress(0)
status_text = str_app.empty()

for i, ticker in enumerate(sector_tickers):
    status_text.text(f"स्कॅन होत आहे: {ticker} ({i+1}/{len(sector_tickers)})")
    try:
        to_date = pd.Timestamp.now().date()
        from_date = to_date.replace(year=to_date.year - 5)
        df_raw = data_provider.get_ohlc_data(ticker, from_date, to_date, active_broker=active_broker)
        df_raw["Date"] = pd.to_datetime(df_raw["Date"])
        analysis = tech.run_advanced_technical_analysis(df_raw, timeframe, index_path)
        if analysis["status"] == "SUCCESS":
            rows.append({
                "Ticker": ticker,
                "Quant Score": analysis["score"],
                "Regime (Pattern)": analysis["regime"].replace("_", " "),
                "Wyckoff Phase": analysis["wyckoff_phase"].split(" (")[0],
                "15D Delivery %": round(analysis["delivery_15d"], 1),
                "Market Gate": analysis["market_gate"].replace("_", " "),
            })
    except FileNotFoundError:
        print(f"[Screener] {ticker}: NSE वरून डेटा मिळाला नाही, वगळत आहे.")
    except Exception as e:
        print(f"[Screener] {ticker} failed: {e}")
    progress.progress((i + 1) / len(sector_tickers))

progress.empty()
status_text.empty()

if not rows:
    str_app.warning("⚠️ या sector मधल्या कुठल्याही ticker साठी NSE वरून डेटा मिळाला नाही (नेटवर्क/NSE सर्व्हर इश्यू असू शकतो).")
    str_app.stop()

result_df = pd.DataFrame(rows).sort_values("Quant Score", ascending=False).reset_index(drop=True)

str_app.dataframe(
    result_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Quant Score": str_app.column_config.ProgressColumn(
            "Quant Score", min_value=0, max_value=100, format="%d"
        ),
    },
)

str_app.caption(
    "⚠️ हे ranking केवळ ऐतिहासिक data-pattern (delivery %, trades, RSI, EMA position) वर आधारित आहे — "
    "गुंतवणूक शिफारस नाही. उच्च स्कोअर म्हणजे 'पॅटर्न-मॅच' जास्त, याचा अर्थ भविष्यातील परतावा नाही."
)
