import streamlit as str_app

import investment_macro as macro
import investment_news as news
from app_state import render_global_sidebar, render_disclaimer_banner
from auth import render_auth_gate

str_app.set_page_config(page_title="Macro & News | Alpha Quant Pro", layout="wide")
render_disclaimer_banner()
authenticator = render_auth_gate()
str_app.title("🌐 Macro & Sector News")

state = render_global_sidebar()
sector, ticker, mapping_df = state["sector"], state["ticker"], state["mapping_df"]
company_row = mapping_df[mapping_df["Ticker"] == ticker]
company_name = company_row["Company_Name"].iloc[0] if not company_row.empty else ""

# ==============================================================================
# 📰 News + Sentiment (RSS-आधारित, keyword sentiment — ML नाही)
# ==============================================================================
str_app.subheader(f"📰 {ticker} ({company_name}) — Latest News")

with str_app.spinner("RSS feeds वरून बातम्या शोधत आहे..."):
    ticker_news = news.get_news_for_ticker(ticker, company_name, max_items=10)

SENTIMENT_COLORS = {"POSITIVE": "#38a169", "NEGATIVE": "#e53e3e", "NEUTRAL": "#718096"}
SENTIMENT_LABEL_MR = {"POSITIVE": "सकारात्मक", "NEGATIVE": "नकारात्मक", "NEUTRAL": "तटस्थ"}

if ticker_news:
    for item in ticker_news:
        color = SENTIMENT_COLORS.get(item["label"], "#718096")
        label_mr = SENTIMENT_LABEL_MR.get(item["label"], item["label"])
        str_app.markdown(
            f"<div class='metric-card' style='text-align:left; margin-bottom:8px; border-left:4px solid {color};'>"
            f"<span style='background-color:{color}; color:white; padding:2px 8px; border-radius:4px; font-size:11px;'>{label_mr}</span> "
            f"<a href='{item['link']}' target='_blank' style='color:#e2e8f0; text-decoration:none;'><b>{item['title']}</b></a><br>"
            f"<span style='font-size:11px; color:#a0aec0;'>{item['source']} · {item['published']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
else:
    str_app.info(
        f"ℹ️ सध्या {ticker} शी संबंधित बातम्या RSS feeds मध्ये सापडल्या नाहीत "
        "(किंवा नेटवर्क/feed उपलब्ध नाही)."
    )

str_app.caption(
    "⚠️ Sentiment हे साधं keyword-based classification आहे (ML मॉडेल नाही) — फक्त दिशादर्शक संकेत, "
    "अचूक भावना-विश्लेषण नाही. बातमीचा मूळ मजकूर वाचूनच निर्णय घ्या."
)

str_app.markdown("---")

# ==============================================================================
# 🌍 Macro (Crude/DXY live + FPI flows)
# ==============================================================================

with str_app.spinner("Live commodity/currency डेटा आणत आहे..."):
    crude_oil_price, dollar_index_dxy, macro_narrative = macro.fetch_global_commodity_trends()
    fpi_flows, fpi_is_real = macro.fetch_nsdl_fpi_flow_report()

c1, c2 = str_app.columns(2)
c1.metric("Crude Oil (WTI, $/barrel)", f"${crude_oil_price:.2f}" if crude_oil_price else "N/A")
c2.metric("Dollar Index (DXY)", f"{dollar_index_dxy:.2f}" if dollar_index_dxy else "N/A")

if macro_narrative:
    str_app.markdown(f"<div class='metric-card' style='text-align:left;'>{macro_narrative}</div>", unsafe_allow_html=True)

str_app.markdown("---")
str_app.subheader(f"💰 FPI Sectoral Flows")

if fpi_is_real:
    flow = fpi_flows.get(sector)
    if flow is not None:
        str_app.metric(f"{sector} — Fortnightly FPI Flow", f"Rs. {flow:,.0f} Cr")
    str_app.dataframe(
        [{"Sector": k, "Flow (Rs. Cr)": v} for k, v in fpi_flows.items()],
        use_container_width=True, hide_index=True,
    )
else:
    str_app.info(
        "ℹ️ FPI sectoral flow डेटा सध्या उपलब्ध नाही — NSDL कडे मोफत real-time API नाही. "
        "[NSDL Reports](https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx) वरून डाउनलोड करून "
        "`fpi_flows_manual.csv` (columns: Sector,Flow_Cr) फाईलमध्ये टाकल्यास इथे दिसेल."
    )

str_app.markdown("---")
str_app.caption(
    "⚠️ हा macro डेटा फक्त संदर्भासाठी (context) आहे — गुंतवणूक निर्णयासाठी थेट आधार मानू नये."
)
