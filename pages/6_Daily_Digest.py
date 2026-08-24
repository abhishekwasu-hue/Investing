import os
import json
from datetime import datetime, date, timedelta
import streamlit as str_app
import pandas as pd

from app_state import render_disclaimer_banner
from auth import render_auth_gate
from nse_holidays import is_nse_trading_holiday

str_app.set_page_config(page_title="Daily Digest | Alpha Quant Pro", layout="wide")
render_disclaimer_banner()
authenticator = render_auth_gate()
str_app.title("🗞️ Daily Sector Digest — AI Scan")

DIGEST_FILE = os.path.join("daily_reports", "latest_digest.json")

if not os.path.exists(DIGEST_FILE):
    str_app.info(
        "ℹ️ अजून कुठलाही daily digest तयार झालेला नाही. GitHub Actions चा 'Daily Sector Scan' "
        "workflow रोज संध्याकाळी आपोआप चालतो (किंवा GitHub च्या Actions टॅबमधून 'Run workflow' "
        "ने आत्ताच manually ट्रिगर करता येतो)."
    )
    str_app.stop()

with open(DIGEST_FILE, "r", encoding="utf-8") as f:
    try:
        digest = json.load(f)
    except json.JSONDecodeError:
        str_app.error("❌ Digest फाईल corrupt आहे — पुढचा scan होईपर्यंत वाट बघा किंवा manually 'Run workflow' ट्रिगर करा.")
        str_app.stop()

KNOWN_SCHEMA_VERSION = 2
file_schema = digest.get("schema_version", 1)
if file_schema > KNOWN_SCHEMA_VERSION:
    str_app.warning(
        f"⚠️ हा digest नवीन format (v{file_schema}) चा आहे, हे page v{KNOWN_SCHEMA_VERSION} साठी बनलंय — "
        "काही fields दिसणार नाहीत. App अपडेट करा."
    )

generated_at = digest.get("generated_at", "N/A")


def _expected_trading_days_missed(generated_date_str: str) -> int:
    """शेवटच्या scan नंतर किती 'ट्रेडिंगचे दिवस' (weekend/NSE holiday वगळून)
    उलटले — रोज-रविवारी उघडलं तरी उगाच 'stale' चा alarm येऊ नये म्हणून."""
    try:
        gen_date = date.fromisoformat(generated_date_str)
    except (ValueError, TypeError):
        return 99  # तारीखच वाचता आली नाही तर सुरक्षिततेसाठी "खूप जुनं" समज
    missed = 0
    d = gen_date + timedelta(days=1)
    while d < date.today():
        is_holiday, _ = is_nse_trading_holiday(d)
        if d.weekday() < 5 and not is_holiday:  # सोम-शुक्र आणि सुट्टी नाही
            missed += 1
        d += timedelta(days=1)
    return missed


trading_days_missed = _expected_trading_days_missed(digest.get("generated_date", ""))

if trading_days_missed >= 2:
    str_app.error(
        f"🔴 **हा डेटा जुना आहे** — शेवटचा यशस्वी scan {trading_days_missed} ट्रेडिंग दिवसांपूर्वीचा आहे "
        f"({generated_at}). GitHub Actions मध्ये scan fail होत असण्याची शक्यता आहे — Actions टॅबमधले "
        f"अलीकडचे runs तपासा."
    )
elif trading_days_missed == 1:
    str_app.warning(f"🟡 शेवटचा scan {generated_at} चा आहे — आज अजून नवीन scan झालेला दिसत नाही.")
else:
    str_app.caption(f"🟢 शेवटचा स्कॅन: {generated_at} | दररोज GitHub Actions द्वारे आपोआप अपडेट होतो")

# ---- AI Commentary ----
str_app.subheader("🤖 AI समालोचन (Claude)")
str_app.markdown(
    f"<div class='metric-card' style='text-align:left; line-height:1.6;'>{digest.get('ai_commentary', 'N/A')}</div>",
    unsafe_allow_html=True,
)

str_app.markdown("---")

# ---- Most Improved Today (day-over-day trend — खरा 'reversal' संकेत) ----
sectors = digest.get("sectors", [])
improving = [s for s in sectors if s.get("trend") == "UP"]
improving.sort(key=lambda s: s.get("score_change", 0), reverse=True)

if improving:
    str_app.subheader("🚀 आज सुधारणा दाखवणारे Sectors (कालच्या तुलनेत)")
    cols = str_app.columns(min(len(improving), 4))
    for i, s in enumerate(improving[:4]):
        with cols[i % 4]:
            str_app.metric(s["sector"], f"{s['avg_quant_score']}/100", delta=f"+{s['score_change']}")
    str_app.markdown("---")
elif any(s.get("trend") == "NEW" for s in sectors):
    str_app.info("ℹ️ हा पहिलाच scan आहे (किंवा history उपलब्ध नाही) — कालच्या तुलनेत बदल उद्यापासून दिसेल.")

# ---- Sector Breadth Table ----
str_app.subheader("📊 Sector Breadth Ranking")
str_app.caption(
    "Wyckoff Breakout % = किती % स्टॉक्समध्ये Wyckoff spring-accumulation पॅटर्न दिसतोय | "
    "Price+Vol Breakout % = किती % स्टॉक्सनी resistance वर, high-volume सह **confirmed** ब्रेकआउट दिला "
    "(institutional सहभागाचा संकेत — जास्त विश्वासार्ह) | "
    "Healthy-Accumulation % = किती % स्टॉक्स तंदुरुस्त संचयन पॅटर्नमध्ये आहेत | "
    "कालच्या तुलनेत = 🟢▲ सुधारणा, 🔴▼ घट, ⚪― स्थिर, 🆕 नवीन (आधीचा डेटा नाही)"
)

TREND_SYMBOL = {"UP": "🟢 ▲", "DOWN": "🔴 ▼", "FLAT": "⚪ ―", "NEW": "🆕"}

if sectors:
    rows = [{
        "Sector": s["sector"],
        "Wyckoff Breakout %": s["reversal_pct"],
        "Price+Vol Breakout %": s.get("breakout_pct", 0.0),
        "Healthy-Accumulation %": s["good_regime_pct"],
        "Avg Quant Score": s["avg_quant_score"],
        "कालच्या तुलनेत": TREND_SYMBOL.get(s.get("trend"), ""),
        "Tickers Scanned": s["total_tickers_scanned"],
    } for s in sectors]
    df = pd.DataFrame(rows)
    str_app.dataframe(
        df, use_container_width=True, hide_index=True,
        column_config={
            "Wyckoff Breakout %": str_app.column_config.ProgressColumn("Wyckoff Breakout %", min_value=0, max_value=100, format="%.0f%%"),
            "Price+Vol Breakout %": str_app.column_config.ProgressColumn("Price+Vol Breakout %", min_value=0, max_value=100, format="%.0f%%"),
            "Healthy-Accumulation %": str_app.column_config.ProgressColumn("Healthy-Accumulation %", min_value=0, max_value=100, format="%.0f%%"),
        },
    )

    str_app.markdown("---")
    str_app.subheader("🏆 आजचे टॉप sectors — तपशील")
    for s in sectors[:5]:
        with str_app.expander(f"📂 {s['sector']} — Price+Vol Breakout {s.get('breakout_pct', 0)}% | Score {s['avg_quant_score']}/100"):
            top_df = pd.DataFrame(s["top_tickers"])
            if not top_df.empty:
                top_df = top_df.rename(columns={
                    "ticker": "Ticker", "score": "Score", "regime": "Regime",
                    "wyckoff_phase": "Wyckoff Phase", "delivery_15d": "15D Delivery %",
                    "is_breakout": "Confirmed Breakout", "volume_ratio": "Volume Ratio",
                })
                str_app.dataframe(top_df, use_container_width=True, hide_index=True)
else:
    str_app.warning("⚠️ आजच्या स्कॅनमध्ये कुठलाही sector डेटा मिळाला नाही.")

str_app.markdown(
    "<p style='font-size:11px; color:#a0aec0; margin-top:20px;'>⚠️ हे केवळ ऐतिहासिक डेटा-पॅटर्न "
    "विश्लेषण (delivery%, RSI, EMA, Wyckoff phase) आहे — AI समालोचनासकट — गुंतवणूक सल्ला नाही. "
    "SEBI-नोंदणीकृत सल्लागाराचा सल्ला घेतल्याशिवाय गुंतवणूक निर्णय घेऊ नका.</p>",
    unsafe_allow_html=True,
)
