import streamlit as str_app
import pandas as pd
import plotly.graph_objects as go

import investment_fundamental as fund
from app_state import render_global_sidebar, render_disclaimer_banner
from auth import render_auth_gate

str_app.set_page_config(page_title="Fundamentals | Alpha Quant Pro", layout="wide")
render_disclaimer_banner()
authenticator = render_auth_gate()
str_app.title("📊 Fundamental Analysis")

state = render_global_sidebar()
ticker, sector, mapping_df = state["ticker"], state["sector"], state["mapping_df"]


def _fmt(v, suffix="", decimals=2):
    return f"{v:.{decimals}f}{suffix}" if v is not None else "N/A"


with str_app.spinner(f"{ticker} साठी Yahoo Finance + financial statements वरून live fundamentals आणत आहे..."):
    result = fund.run_advanced_fundamental_analysis(ticker)
    quarterly_rows = fund.get_quarterly_earnings_table(ticker, n_quarters=6)

str_app.caption(f"Source: {result['data_source']}")

# ---- Top-line score + market cap ----
c1, c2 = str_app.columns([1, 3])
c1.metric("Fundamental Score", f"{result['fundamental_score']}/100")
c2.markdown(
    f"<div class='metric-card' style='text-align:left; height:100%; display:flex; align-items:center;'>"
    f"<b>Market Cap:</b>&nbsp; {_fmt(result['market_cap_cr'], ' Cr', 0) if result['market_cap_cr'] else 'N/A'}"
    f"</div>",
    unsafe_allow_html=True,
)

str_app.markdown("---")

# ---- Pros & Cons (Screener.in चं सिग्नेचर फीचर) ----
pros, cons = result.get("pros", []), result.get("cons", [])
if pros or cons:
    str_app.subheader("⚖️ Pros & Cons — निरीक्षणं (सल्ला नाही)")
    pc1, pc2 = str_app.columns(2)
    with pc1:
        st_ = str_app.container(border=True)
        st_.markdown("**✅ Pros**")
        if pros:
            for p in pros:
                st_.markdown(f"- {p}")
        else:
            st_.caption("सध्याच्या आकड्यांनुसार ठळक pros आढळले नाहीत.")
    with pc2:
        st_ = str_app.container(border=True)
        st_.markdown("**⚠️ Cons**")
        if cons:
            for c in cons:
                st_.markdown(f"- {c}")
        else:
            st_.caption("सध्याच्या आकड्यांनुसार ठळक cons आढळले नाहीत.")
    str_app.caption(
        "⚠️ ही यादी वरच्या ratios वरून साध्या नियमांनी (rule-based) आपोआप तयार होते — "
        "स्वतंत्र गुणात्मक विश्लेषण नाही, आणि गुंतवणूक शिफारस नाही."
    )
    str_app.markdown("---")
str_app.subheader("💰 Valuation")
v1, v2, v3, v4, v5 = str_app.columns(5)
v1.metric("PE Ratio", _fmt(result["pe_ratio"], decimals=1))
v2.metric("PB Ratio", _fmt(result["pb_ratio"], decimals=2))
v3.metric("EV/EBITDA", _fmt(result["ev_ebitda"], decimals=1))
v4.metric("Price/Sales", _fmt(result["price_to_sales"], decimals=2))
v5.metric("Dividend Yield", _fmt(result["dividend_yield"], "%", 2))

# ---- Section 2: Profitability ----
str_app.subheader("📈 Profitability")
p1, p2, p3, p4, p5, p6 = str_app.columns(6)
p1.metric("ROE", _fmt(result["roe"], "%", 1))
p2.metric("ROCE", _fmt(result["roce"], "%", 1))
p3.metric("ROA", _fmt(result["roa"], "%", 1))
p4.metric("Operating Margin", _fmt(result["operating_margin"], "%", 1))
p5.metric("Net Margin", _fmt(result["net_margin"], "%", 1))
p6.metric("Gross Margin", _fmt(result["gross_margin"], "%", 1))

# ---- Section 3: Financial Health ----
str_app.subheader("🏦 Financial Health")
f1, f2, f3 = str_app.columns(3)
f1.metric("Debt/Equity", _fmt(result["debt_to_equity"], decimals=2))
f2.metric("Current Ratio", _fmt(result["current_ratio"], decimals=2))
f3.metric("Book Value/Share", _fmt(result["book_value_per_share"], decimals=1))

# ---- Section 3b: Working Capital Cycle (Screener.in स्टाईल) ----
str_app.subheader("🔄 Working Capital Cycle")
w1, w2, w3, w4 = str_app.columns(4)
w1.metric("Debtor Days", _fmt(result["debtor_days"], " दिवस", 0))
w2.metric("Inventory Days", _fmt(result["inventory_days"], " दिवस", 0))
w3.metric("Payable Days", _fmt(result["payable_days"], " दिवस", 0))
w4.metric("Cash Conversion Cycle", _fmt(result["cash_conversion_cycle"], " दिवस", 0))
str_app.caption("Cash Conversion Cycle = Debtor Days + Inventory Days − Payable Days. कमी असणं (किंवा negative) सहसा चांगलं — पैसे व्यवसायात कमी काळ अडकतात.")

# ---- Section 4: Growth ----
str_app.subheader("🚀 Growth (Annual CAGR)")
g1, g2 = str_app.columns(2)
sg, pg = result["sales_growth_3y"], result["profit_growth_3y"]
g1.metric("Sales CAGR", f"{sg*100:.1f}%" if sg is not None else "N/A")
g2.metric("Profit CAGR", f"{pg*100:.1f}%" if pg is not None else "N/A")

# ---- Section 5: Cash Flow ----
str_app.subheader("💵 Cash Flow")
cf1, cf2, cf3 = str_app.columns(3)
cf1.metric("Free Cash Flow", result["free_cash_flow"])
cf2.metric("FCF (Rs. Cr)", _fmt(result["free_cash_flow_cr"], " Cr", 0) if result["free_cash_flow_cr"] else "N/A")
cf3.metric("Operating CF (Rs. Cr)", _fmt(result["operating_cf_cr"], " Cr", 0) if result["operating_cf_cr"] else "N/A")

str_app.markdown("---")

str_app.markdown("---")

# ---- Multi-Year Annual P&L Trend (Screener.in च्या मुख्य टेबलसारखं) ----
str_app.subheader(f"📅 वार्षिक Profit & Loss Trend — {ticker}")
with str_app.spinner("वार्षिक financial statements आणत आहे..."):
    yearly_rows = fund.get_multi_year_financials(ticker, years=5)

if yearly_rows:
    ydf = pd.DataFrame(yearly_rows)
    yearly_fig = go.Figure()
    yearly_fig.add_trace(go.Bar(x=ydf["year"], y=ydf["sales_cr"], name="Sales (Rs. Cr)", marker_color="#3182ce"))
    yearly_fig.add_trace(go.Bar(x=ydf["year"], y=ydf["net_profit_cr"], name="Net Profit (Rs. Cr)", marker_color="#38a169"))
    yearly_fig.update_layout(
        barmode="group", height=320, template="plotly_dark",
        margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="#0b0e14", plot_bgcolor="#0b0e14",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    str_app.plotly_chart(yearly_fig, use_container_width=True)

    yearly_display = ydf.rename(columns={
        "year": "Year", "sales_cr": "Sales (Rs. Cr)", "net_profit_cr": "Net Profit (Rs. Cr)", "opm_pct": "OPM %",
    })
    str_app.dataframe(yearly_display, use_container_width=True, hide_index=True)
    str_app.caption(
        f"Yahoo Finance कडून उपलब्ध शेवटची {len(yearly_rows)} वर्षं. "
        "Screener.in सारख्या स्रोतांकडे १०+ वर्षांचा इतिहास असतो — तो मोफत API मधून मिळत नाही, "
        "ही एक प्रामाणिक मर्यादा आहे."
    )
else:
    str_app.warning("⚠️ वार्षिक financial data सध्या उपलब्ध नाही.")

# ---- Quarterly trend — टेबल + चार्ट दोन्ही ----
str_app.subheader(f"📈 तिमाही Sales & Net Profit — {ticker}")

if quarterly_rows:
    qdf = pd.DataFrame(quarterly_rows)

    trend_fig = go.Figure()
    trend_fig.add_trace(go.Bar(x=qdf["quarter"], y=qdf["sales_cr"], name="Sales (Rs. Cr)", marker_color="#3182ce"))
    trend_fig.add_trace(go.Bar(x=qdf["quarter"], y=qdf["profit_cr"], name="Net Profit (Rs. Cr)", marker_color="#38a169"))
    trend_fig.update_layout(
        barmode="group", height=350, template="plotly_dark",
        margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="#0b0e14", plot_bgcolor="#0b0e14",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    str_app.plotly_chart(trend_fig, use_container_width=True)

    display_df = qdf.rename(columns={
        "quarter": "Quarter", "sales_cr": "Sales (Rs. Cr)",
        "profit_cr": "Net Profit (Rs. Cr)", "qoq_growth_pct": "QoQ Sales Growth %",
    })
    str_app.dataframe(display_df, use_container_width=True, hide_index=True)
    str_app.caption(f"Yahoo Finance कडून उपलब्ध शेवटचे {len(quarterly_rows)} तिमाही आकडे. सहसा ४-५ तिमाहीच उपलब्ध असतात.")
else:
    str_app.warning("⚠️ या ticker साठी तिमाही earnings डेटा सध्या Yahoo Finance वरून उपलब्ध नाही.")


# ---- Peer Comparison (same micro-sector) ----
str_app.markdown("---")
str_app.subheader(f"🔍 Peer Comparison — {sector}")

peer_tickers = mapping_df[mapping_df["Micro_Sector"] == sector]["Ticker"].tolist()
peer_tickers = [t for t in peer_tickers if t != ticker]

if peer_tickers:
    with str_app.spinner(f"{sector} मधल्या इतर कंपन्यांचा डेटा आणत आहे (जास्तीत जास्त ६)..."):
        peer_rows = fund.get_peer_comparison(peer_tickers, max_peers=6)
        # निवडलेला ticker स्वतःही तुलनेत दाखवतो, वरती ठेवून
        peer_rows.insert(0, {
            "Ticker": f"{ticker} (निवडलेला)", "Score": result["fundamental_score"],
            "PE": result["pe_ratio"], "ROE %": result["roe"],
            "Debt/Equity": result["debt_to_equity"], "Net Margin %": result["net_margin"],
        })
    if len(peer_rows) > 1:
        peer_df = pd.DataFrame(peer_rows)
        str_app.dataframe(
            peer_df, use_container_width=True, hide_index=True,
            column_config={"Score": str_app.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d")},
        )
    else:
        str_app.info("ℹ️ Peer तुलनेसाठी पुरेसा डेटा मिळाला नाही.")
else:
    str_app.info("ℹ️ या micro-sector मध्ये इतर कंपन्या मॅपिंगमध्ये नाहीत.")

str_app.markdown(
    "<p style='font-size:11px; color:#a0aec0; margin-top:20px;'>⚠️ हे आकडे केवळ माहितीसाठी आहेत, "
    "गुंतवणूक सल्ला नाहीत. काही आकडे थेट Yahoo Finance वरून, तर काही (ROE/ROCE/Debt-Equity/Current Ratio/"
    "Working Capital Cycle इ.) कंपनीच्या ताज्या financial statements मधून calculate केलेले आहेत — तरीही "
    "चुकीचे/जुने असू शकतात, कंपनीच्या अधिकृत फायलिंगशी पडताळून घ्या.<br><br>"
    "<b>Screener.in शी तुलनेत एक स्पष्ट मर्यादा:</b> Shareholding Pattern (Promoter/FII/DII/Public होल्डिंग "
    "ट्रेंड) इथे नाही — ही NSE/BSE corporate filings मधून येणारी माहिती आहे, Yahoo Finance च्या मोफत API "
    "मध्ये उपलब्ध नाही. हवी असल्यास प्रत्यक्ष NSE वेबसाइट किंवा Screener.in वर बघावी लागेल.</p>",
    unsafe_allow_html=True,
)
