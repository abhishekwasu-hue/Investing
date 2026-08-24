import streamlit as str_app
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime

import investment_technical as tech
import investment_fundamental as fund
import data_provider
from app_state import render_global_sidebar, render_disclaimer_banner, DB_FOLDER, ensure_index_data_path
import os
from auth import render_auth_gate
import subscription

# ==============================================================================
# 🎨 प्रगत थीम आणि प्रिमियम UI लेआउट (Premium Institutional Layout Grid)
# ==============================================================================
str_app.set_page_config(page_title="Alpha Quant Pro Terminal", layout="wide")

str_app.markdown("""
    <style>
        .main { background-color: #0b0e14; }
        div.stDownloadButton > button { color: white !important; border-radius: 6px !important; font-weight: bold !important; width: 100% !important; height: 45px !important; margin-bottom: 10px !important; }
        .metric-card { background-color: #131722; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39; color: white; text-align: center; }
    </style>
""", unsafe_allow_html=True)

str_app.title("🏆 ALPHA UNIVERSAL INVESTMENT TERMINAL (PRO)")
render_disclaimer_banner()

# ---- Login gate — पुढे काहीही दाखवण्याआधी ----
authenticator = render_auth_gate()
username = str_app.session_state["username"]
tier = subscription.get_tier(username)

str_app.sidebar.markdown(f"👤 **{str_app.session_state.get('name', username)}**")
badge = "⭐ PRO" if tier == "PRO" else "🆓 Free"
str_app.sidebar.markdown(f"Plan: **{badge}**")
if tier == "FREE":
    str_app.sidebar.caption(f"PDF reports आज: {subscription.usage_today(username, 'pdf_report')}/{subscription.FREE_LIMITS['pdf_report']}")
    str_app.sidebar.caption("⭐ Unlimited साठी वरच्या page-list मधून 'Upgrade to Pro' उघडा.")
authenticator.logout(location="sidebar")
str_app.sidebar.markdown("---")

str_app.markdown(
    "<p style='color:#718096; font-size:14px; margin-top:-15px;'>"
    "<b>Overview | बाकी सगळं sidebar वरच्या pages मध्ये: Technical Chart · Fundamentals · Sector Screener · Macro/News</b></p>",
    unsafe_allow_html=True,
)

# ---- Sidebar (सगळ्या pages मध्ये common — app_state.py मध्ये) ----
state = render_global_sidebar()
selected_ticker, selected_sector = state["ticker"], state["sector"]
timeframe, active_broker = state["timeframe"], state["active_broker"]

live_ltp = data_provider.get_live_ltp(selected_ticker, active_broker=active_broker)
if live_ltp is not None:
    str_app.sidebar.metric(f"🔴 LIVE — {selected_ticker}", f"₹{live_ltp:,.2f}")
else:
    str_app.sidebar.caption("ℹ️ Live price नाही — शेवटची saved किंमत (delayed).")

# ==============================================================================
# 🧠 डेटा लोड + विश्लेषण (broker-agnostic, आपोआप free-data fallback)
# ==============================================================================
index_path = ensure_index_data_path()
is_intraday_tf = timeframe.startswith("75-Minute")

if is_intraday_tf:
    if active_broker is None or not active_broker.is_connected():
        str_app.warning(
            "⚠️ 75-Minute (इंट्रा-डे) साठी मिनिट-स्तरीय डेटा लागतो, जो फक्त live broker जोडलेला "
            "असेल तरच (उदा. Upstox — sidebar मध्ये) मिळतो. NSE/Yahoo कडे फक्त daily डेटा असतो. "
            "सध्या Daily/Weekly/Monthly निवडा, किंवा sidebar मधून broker जोडा."
        )
        str_app.stop()
    with str_app.spinner(f"{selected_ticker} साठी intraday डेटा आणत आहे..."):
        to_date = datetime.now().date()
        from_date = to_date - pd.Timedelta(days=60)
        df_raw = data_provider.get_intraday_ohlc_data(selected_ticker, from_date, to_date, active_broker=active_broker)
    if df_raw is None or df_raw.empty:
        str_app.error(f"❌ {active_broker.display_name()} कडून intraday डेटा मिळाला नाही.")
        str_app.stop()
else:
    try:
        to_date = datetime.now().date()
        from_date = to_date.replace(year=to_date.year - 5)
        with str_app.spinner(f"{selected_ticker} साठी डेटा तयार करत आहे (पहिल्यांदाच थोडा वेळ लागू शकतो)..."):
            df_raw = data_provider.get_ohlc_data(selected_ticker, from_date, to_date, active_broker=active_broker)
    except FileNotFoundError as e:
        str_app.error(f"❌ {e}")
        str_app.stop()

df_raw["Date"] = pd.to_datetime(df_raw["Date"])
analysis = tech.run_advanced_technical_analysis(df_raw, timeframe, index_path)

if analysis["status"] != "SUCCESS":
    str_app.error("❌ पुरेसा डेटा उपलब्ध नाही — आधी `investment_database.py` चालवा.")
    str_app.stop()

quant_score = analysis["score"]
research_text = analysis["reason"]
market_gate = analysis["market_gate"]
delivery_15d = analysis["delivery_15d"]
wyckoff_phase = analysis["wyckoff_phase"]

c1, c2, c3 = str_app.columns(3)
c1.metric("Quant Score", f"{quant_score}/100")
c2.metric("15D Avg Delivery %", f"{delivery_15d:.1f}%")
c3.metric("Market Gate (NIFTY proxy)", market_gate.replace("_", " "))
str_app.info("👉 सविस्तर candlestick chart साठी sidebar वरून **📈 Technical Chart** page उघडा.")

# ==============================================================================
# 🧱 ड्युअल रिपोर्ट जनरेशन इंजिन (Stock-Specific Report)
# ==============================================================================
current_date_str = datetime.now().strftime('%d-%b-%Y')

quarterly_rows = fund.get_quarterly_earnings_table(selected_ticker, n_quarters=6)

if quarterly_rows:
    table_rows_html = ""
    for row in quarterly_rows:
        growth = row["qoq_growth_pct"]
        if growth is None:
            growth_html = "<td>N/A</td>"
        elif growth >= 0:
            growth_html = f"<td style='color:green; font-weight:bold;'>+{growth:.1f}%</td>"
        else:
            growth_html = f"<td style='color:red;'>{growth:.1f}%</td>"
        profit_display = f"Rs. {row['profit_cr']:,.0f} Cr" if row["profit_cr"] is not None else "N/A"
        table_rows_html += (
            f"<tr><td><b>{row['quarter']}</b></td>"
            f"<td>Rs. {row['sales_cr']:,.0f} Cr</td>"
            f"<td>{profit_display}</td>"
            f"{growth_html}</tr>"
        )
    earnings_table_html = f"""
<table style='width:100%; border-collapse:collapse; margin-top:15px; font-size:13px;'>
    <tr style='background-color:#1a365d; color:white;'>
        <th style='padding:8px; border:1px solid #cbd5e0;'>तिमाही सत्र (Quarter)</th>
        <th style='padding:8px; border:1px solid #cbd5e0;'>एकूण विक्री (Sales Cr.)</th>
        <th style='padding:8px; border:1px solid #cbd5e0;'>निव्वळ शुद्ध नफा (Net Profit Cr.)</th>
        <th style='padding:8px; border:1px solid #cbd5e0;'>Q-o-Q वृद्धी (Growth Matrix)</th>
    </tr>
    {table_rows_html}
</table>
<p style='font-size:11px; color:#a0aec0; margin-top:5px;'>Source: Yahoo Finance (live) — शेवटचे {len(quarterly_rows)} तिमाही रिपोर्ट्स.</p>
"""
else:
    earnings_table_html = "<p style='color:#e53e3e; font-size:13px;'>⚠️ या ticker साठी तिमाही अर्निंग्स डेटा सध्या उपलब्ध नाही.</p>"

stock_report_html = f"""
<html>
<body style='font-family: Arial, sans-serif; padding: 35px; color: #2d3748;'>
    <div style='max-width: 800px; margin: 0 auto; border: 1px solid #1a365d; padding: 40px; border-radius: 8px; background-color:#ffffff;'>
        <h2 style='color:#1a365d; text-align:center; margin-top:0;'>🏆 ALPHA QUANT STOCK SPECIFIC REPORT (PRO)</h2>
        <p style='text-align:center; color:#718096;'>📅 <b>दिनांक:</b> {current_date_str} | <b>लक्ष्य कंपनी:</b> {selected_ticker} ({selected_sector})</p>
        <hr style='border: 1px solid #3182ce; margin:20px 0;'>

        <h3 style='color:#1a365d; border-bottom:1px solid #cbd5e0; padding-bottom:5px;'>📈 १. तिमाही अर्निंग्स विश्लेषण</h3>
        {earnings_table_html}

        <h3 style='color:#1a365d; border-bottom:1px solid #cbd5e0; padding-bottom:5px; margin-top:30px;'>🕯️ २. Technical Structure</h3>
        <p style='font-size:13px;'>सध्याचा Wyckoff phase पॅटर्न: <b>{wyckoff_phase}</b>.</p>

        <h3 style='color:#1a365d; border-bottom:1px solid #cbd5e0; padding-bottom:5px; margin-top:30px;'>📥 ३. डिलिव्हरी आणि व्हॉल्युम विश्लेषण</h3>
        <p style='font-size:13.5px; background-color:#ebf8ff; padding:15px; border-left:4px solid #3182ce; border-radius:4px; line-height:1.5;'>
            <b>अल्गो निरीक्षण (Observation, सल्ला नाही):</b> {research_text} <b>Quant Score: {quant_score}/100</b>
        </p>
        <p style='font-size:11px; color:#a0aec0; margin-top:15px; border-top:1px solid #e2e8f0; padding-top:10px;'>
            ⚠️ <b>Disclaimer:</b> हा रिपोर्ट केवळ शैक्षणिक/माहितीच्या उद्देशाने ऐतिहासिक डेटा-पॅटर्न विश्लेषणावर आधारित आहे. हा SEBI-नोंदणीकृत गुंतवणूक सल्ला नाही. गुंतवणुकीचे निर्णय घेण्यापूर्वी स्वतःचं संशोधन करा किंवा SEBI-नोंदणीकृत गुंतवणूक सल्लागाराचा सल्ला घ्या.
        </p>
    </div>
</body>
</html>
"""

str_app.markdown("---")
str_app.subheader("🟩 Stock-Specific Report")
components.html(stock_report_html, height=600, scrolling=True)

col_a, col_b = str_app.columns(2)
with col_a:
    str_app.download_button(
        "⬇️ Download Report (HTML)", data=stock_report_html,
        file_name=f"{selected_ticker}_report_{current_date_str}.html", mime="text/html",
    )
with col_b:
    if str_app.button("📄 Generate PDF Report"):
        if not subscription.check_and_increment(username, "pdf_report"):
            str_app.error(
                f"⚠️ आजची Free-tier मर्यादा ({subscription.FREE_LIMITS['pdf_report']} PDF reports/दिवस) संपली. "
                "उद्या पुन्हा प्रयत्न करा, किंवा Unlimited साठी sidebar वरून Upgrade to Pro करा."
            )
            str_app.stop()
        with str_app.spinner("PDF तयार होत आहे (chart image + fundamentals + earnings)..."):
            from chart_builder import build_technical_chart
            from report_pdf_generator import build_stock_report_pdf
            import investment_macro as macro
            import investment_news as news

            chart_fig = build_technical_chart(analysis["chart_data"], analysis, selected_ticker, timeframe)
            crude, dxy, narrative = macro.fetch_global_commodity_trends()
            company_row = state["mapping_df"][state["mapping_df"]["Ticker"] == selected_ticker]
            company_name = company_row["Company_Name"].iloc[0] if not company_row.empty else ""
            news_items = news.get_news_for_ticker(selected_ticker, company_name, max_items=8)
            pdf_bytes = build_stock_report_pdf(
                ticker=selected_ticker,
                sector=selected_sector,
                analysis=analysis,
                fundamental_result=fund.run_advanced_fundamental_analysis(selected_ticker),
                quarterly_rows=quarterly_rows,
                macro_data={"crude_oil_price": crude, "dollar_index_dxy": dxy, "narrative": narrative},
                chart_fig=chart_fig,
                news_items=news_items,
            )
        str_app.download_button(
            "⬇️ Download Report (PDF)", data=pdf_bytes,
            file_name=f"{selected_ticker}_research_report_{current_date_str}.pdf", mime="application/pdf",
        )
