import streamlit as str_app
import pandas as pd

import investment_fundamental as fund
from app_state import render_global_sidebar, render_disclaimer_banner
from auth import render_auth_gate

str_app.set_page_config(page_title="Fundamentals | Alpha Quant Pro", layout="wide")
render_disclaimer_banner()
authenticator = render_auth_gate()
str_app.title("📊 Fundamental Analysis")

state = render_global_sidebar()
ticker = state["ticker"]

with str_app.spinner(f"{ticker} साठी Yahoo Finance वरून live fundamentals आणत आहे..."):
    result = fund.run_advanced_fundamental_analysis(ticker)
    quarterly_rows = fund.get_quarterly_earnings_table(ticker, n_quarters=6)

str_app.caption(f"Source: {result['data_source']}")

c1, c2, c3, c4, c5 = str_app.columns(5)
c1.metric("Fundamental Score", f"{result['fundamental_score']}/100")
c2.metric("PE Ratio", f"{result['pe_ratio']:.1f}" if result["pe_ratio"] else "N/A")
c3.metric("ROE", f"{result['roe']:.1f}%" if result["roe"] is not None else "N/A")
c4.metric("Debt/Equity", f"{result['debt_to_equity']:.2f}" if result["debt_to_equity"] is not None else "N/A")
c5.metric("Free Cash Flow", result["free_cash_flow"])

c6, c7 = str_app.columns(2)
sg = result["sales_growth_3y"]
pg = result["profit_growth_3y"]
c6.metric("Sales CAGR (annual growth)", f"{sg*100:.1f}%" if sg is not None else "N/A")
c7.metric("Profit CAGR (annual growth)", f"{pg*100:.1f}%" if pg is not None else "N/A")

str_app.markdown("---")
str_app.subheader(f"📈 तिमाही Sales & Net Profit — {ticker}")

if quarterly_rows:
    df = pd.DataFrame(quarterly_rows)
    df = df.rename(columns={
        "quarter": "Quarter", "sales_cr": "Sales (Rs. Cr)",
        "profit_cr": "Net Profit (Rs. Cr)", "qoq_growth_pct": "QoQ Sales Growth %",
    })
    str_app.dataframe(df, use_container_width=True, hide_index=True)
    str_app.caption(f"Yahoo Finance कडून उपलब्ध शेवटचे {len(quarterly_rows)} तिमाही आकडे. सहसा ४-५ तिमाहीच उपलब्ध असतात.")
else:
    str_app.warning("⚠️ या ticker साठी तिमाही earnings डेटा सध्या Yahoo Finance वरून उपलब्ध नाही.")

str_app.markdown(
    "<p style='font-size:11px; color:#a0aec0; margin-top:20px;'>⚠️ हे आकडे केवळ माहितीसाठी आहेत, "
    "गुंतवणूक सल्ला नाहीत. आकडे चुकीचे/जुने असू शकतात — कंपनीच्या अधिकृत फायलिंगशी पडताळून घ्या.</p>",
    unsafe_allow_html=True,
)
