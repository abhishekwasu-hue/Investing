"""
Daily Sector Reversal / Opportunity Scanner + AI Commentary Agent.

हे script GitHub Actions cron (.github/workflows/daily_scan.yml) रोज चालवतो
(मार्केट बंद झाल्यावर). काम असं:

  1. investment_master_mapping.csv मधल्या सगळ्या micro-sectors आणि त्यातल्या
     tickers साठी existing तांत्रिक इंजिन (investment_technical.py) वापरून
     स्कॅन करतो — नवीन/वेगळं लॉजिक नाही, तोच विश्वासार्ह इंजिन.
  2. प्रत्येक sector साठी "breadth" काढतो — त्या sector मधल्या किती %
     tickers मध्ये Wyckoff breakout (PHASE_C) किंवा healthy-accumulation
     पॅटर्न दिसतोय. एक-दोन स्टॉक्स नाही तर संपूर्ण sector मध्ये तेजी
     दिसली तरच तो खरा "sector rotation" संकेत मानतो.
  3. Claude API ला हा सारांश देऊन वर्णनात्मक (सल्ला नाही) समालोचन लिहायला
     सांगतो.
  4. निकाल daily_reports/latest_digest.json मध्ये सेव्ह करतो — हीच फाईल
     Streamlit app च्या "Daily Digest" पानावर दाखवली जाते. GitHub Actions
     ही फाईल परत repo मध्ये commit करतो, त्यामुळे Streamlit Cloud आपोआप
     redeploy होऊन नवीन डेटा दाखवतो.
  5. ऐच्छिकपणे ईमेल डायजेस्टही पाठवतो (SMTP — Gmail App Password वापरून).

स्वतंत्रपणे टेस्ट करण्यासाठी: python daily_scan_agent.py
"""

import os
import json
import time
import smtplib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

import pandas as pd

import investment_technical as tech
from broker_adapters.free_data_adapter import FreeDataAdapter
from nse_holidays import is_nse_trading_holiday

MAPPING_FILE = "investment_master_mapping.csv"
OUTPUT_DIR = "daily_reports"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "latest_digest.json")

# digest JSON फॉरमॅट बदलला (नवीन field जोडलं/जुनं काढलं) की हा वाढवा —
# जुन्या स्वरूपाच्या फाईल्स वाचताना graceful handling करता येतं (crash नाही)
SCHEMA_VERSION = 2

GOOD_REGIMES = ["STABLE_ACCUMULATION", "HEALTHY_PRICE_CORRECTION"]

# ⚠️ Trade-off, blind "जास्त parallel = चांगलं" नाही: जास्त workers म्हणजे
# स्कॅन जलद होतो, पण एकाच वेळी NSE ला जास्त requests एकाच (GitHub Actions)
# IP वरून गेल्याने rate-limit/block होण्याची शक्यता वाढते. ४ हे संतुलित
# डीफॉल्ट आहे. जास्त failures दिसू लागले तर env var ने कमी करा:
#   SCAN_MAX_WORKERS=1  (पूर्णपणे sequential, जुन्या पद्धतीसारखं)
MAX_PARALLEL_WORKERS = int(os.environ.get("SCAN_MAX_WORKERS", "4"))

# Sanity-check thresholds — यापेक्षा कमी sectors/tickers स्कॅन झाले तर
# "आज खरंच शांत मार्केट आहे" असं समजण्याऐवजी "स्कॅन engine मध्येच काहीतरी
# बिघडलंय" (उदा. NSE+Yahoo दोन्ही एकाच वेळी block) असा संशय घेतो.
MIN_SECTORS_FOR_HEALTHY_SCAN = 5
MIN_TICKERS_FOR_HEALTHY_SCAN = 20


def _fetch_with_retry(free_adapter, ticker, from_date, to_date, max_retries=2, backoff_seconds=3):
    """क्षणिक (transient) network/API अडचणीमुळे एखादा ticker स्किप होऊ नये
    म्हणून थोडा वेळ थांबून पुन्हा प्रयत्न करतो. सलग सगळे प्रयत्न fail
    झाले तरच None परत देतो — तेव्हा तो ticker त्या दिवसासाठी वगळला जातो,
    संपूर्ण scan crash होत नाही."""
    last_error = None
    for attempt in range(1, max_retries + 2):
        try:
            df = free_adapter.get_historical(ticker, from_date, to_date)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            last_error = e
        if attempt <= max_retries:
            print(f"[DailyScan] {ticker}: प्रयत्न {attempt} अयशस्वी, {backoff_seconds}s थांबून पुन्हा प्रयत्न...")
            time.sleep(backoff_seconds)
    if last_error:
        print(f"[DailyScan] {ticker}: {max_retries + 1} प्रयत्नांनंतरही अयशस्वी: {last_error}")
    return None


def _scan_one_ticker(free_adapter, ticker: str):
    """एका ticker साठी fetch + technical analysis — parallel worker मध्ये चालतं."""
    try:
        to_date = date.today()
        from_date = to_date.replace(year=to_date.year - 2)
        df_raw = _fetch_with_retry(free_adapter, ticker, from_date, to_date)
        if df_raw is None or df_raw.empty:
            return None
        analysis = tech.run_advanced_technical_analysis(df_raw, "Daily (दैनिक)", None)
        if analysis["status"] != "SUCCESS":
            return None
        breakout = analysis.get("breakout") or {}
        supertrend = analysis.get("supertrend") or {}
        return {
            "ticker": ticker,
            "score": analysis["score"],
            "regime": analysis["regime"],
            "wyckoff_phase": analysis["wyckoff_phase"],
            "delivery_15d": round(analysis["delivery_15d"], 1),
            "is_breakout": bool(breakout.get("is_breakout")),
            "volume_ratio": breakout.get("volume_ratio"),
            "supertrend_flipped": bool(supertrend.get("flipped")),
            "supertrend_direction": supertrend.get("direction"),
        }
    except Exception as e:
        print(f"[DailyScan] {ticker} failed: {e}")
        return None


def scan_all_sectors(max_tickers_per_sector: int = None, max_workers: int = None) -> list:
    """
    प्रत्येक micro-sector स्कॅन करून breadth-आधारित ranking देतो.
    max_tickers_per_sector: टेस्टिंगसाठी मर्यादा घालायची असल्यास (None = सगळे).
    max_workers: parallel fetch workers (None = MAX_PARALLEL_WORKERS डीफॉल्ट).

    Fetch (network I/O) parallel केला आहे, पण sector-level aggregation
    (गणित) मुद्दाम sequential ठेवलंय — ते इतकं हलकं आहे की parallel करून
    फायदा नाही, आणि race-condition चा धोकाही नको.
    """
    mapping_df = pd.read_csv(MAPPING_FILE)
    sectors = mapping_df["Micro_Sector"].unique().tolist()
    free_adapter = FreeDataAdapter()
    max_workers = max_workers or MAX_PARALLEL_WORKERS

    sector_tickers = {}
    all_tickers = []
    for sector in sectors:
        tickers = mapping_df[mapping_df["Micro_Sector"] == sector]["Ticker"].tolist()
        if max_tickers_per_sector:
            tickers = tickers[:max_tickers_per_sector]
        sector_tickers[sector] = tickers
        all_tickers.extend(tickers)

    # ---- Parallel fetch (network-bound असल्याने threads योग्य, processes नाही) ----
    ticker_results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(_scan_one_ticker, free_adapter, ticker): ticker
            for ticker in all_tickers
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                ticker_results[ticker] = future.result()
            except Exception as e:
                print(f"[DailyScan] {ticker}: worker मध्ये अनपेक्षित error: {e}")
                ticker_results[ticker] = None

    # ---- Sector-level aggregation (sequential — निकाल नेहमी एकसारखेच येतात, thread-order वर अवलंबून नाही) ----
    sector_results = []
    for sector, tickers in sector_tickers.items():
        stock_rows = [ticker_results.get(t) for t in tickers]
        stock_rows = [r for r in stock_rows if r is not None]

        if not stock_rows:
            continue

        total = len(stock_rows)
        reversal_count = sum(1 for r in stock_rows if r["wyckoff_phase"].startswith("PHASE_C"))
        good_regime_count = sum(1 for r in stock_rows if r["regime"] in GOOD_REGIMES)
        breakout_count = sum(1 for r in stock_rows if r["is_breakout"])
        avg_score = sum(r["score"] for r in stock_rows) / total

        sector_results.append({
            "sector": sector,
            "total_tickers_scanned": total,
            "reversal_pct": round(reversal_count / total * 100, 1),
            "good_regime_pct": round(good_regime_count / total * 100, 1),
            "breakout_pct": round(breakout_count / total * 100, 1),
            "avg_quant_score": round(avg_score, 1),
            "top_tickers": sorted(stock_rows, key=lambda r: (r["is_breakout"], r["score"]), reverse=True)[:5],
        })

    # सर्वात जास्त reversal + healthy-accumulation + breakout breadth असलेले sectors वर
    sector_results.sort(key=lambda s: s["reversal_pct"] + s["good_regime_pct"] + s["breakout_pct"], reverse=True)
    return sector_results


HISTORY_DIR = os.path.join(OUTPUT_DIR, "history")
HISTORY_RETENTION_DAYS = 30


def _load_previous_digest():
    """History मधला सर्वात अलीकडचा (आजचा नाही) digest शोधतो — day-over-day
    तुलनेसाठी लागतो. आधीचा डेटाच नसेल (पहिलाच run), फाईल corrupt असेल,
    किंवा भविष्यातल्या अनोळखी schema version ची असेल — तर None (crash
    नाही, फक्त trend='NEW' दाखवला जाईल)."""
    if not os.path.isdir(HISTORY_DIR):
        return None
    today_str = date.today().isoformat()
    files = sorted(
        f for f in os.listdir(HISTORY_DIR)
        if f.endswith(".json") and f.replace(".json", "") != today_str
    )
    if not files:
        return None

    with open(os.path.join(HISTORY_DIR, files[-1]), "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[DailyScan] जुनी history फाईल corrupt आहे, वगळतो: {e}")
            return None

    file_version = data.get("schema_version", 1)  # schema_version नसेल तर सगळ्यात जुनी (v1) समज
    if file_version > SCHEMA_VERSION:
        # भविष्यातल्या (आपल्याला माहीत नसलेल्या) format ची फाईल — जबरदस्तीने
        # वाचून चुकीचा trend दाखवण्यापेक्षा वगळणं सुरक्षित
        print(f"[DailyScan] History फाईल schema_version={file_version} आपल्या {SCHEMA_VERSION} पेक्षा नवीन आहे — वगळतो.")
        return None
    # file_version < SCHEMA_VERSION (जुनी फाईल) असेल तरी ठीक आहे — sectors
    # मधले नवीन fields फक्त .get() ने वाचले जातात, missing असतील तर None/NEW
    return data


def compute_trend(sector_results: list, previous_digest: dict) -> list:
    """
    प्रत्येक sector ला आधीच्या (शेवटच्या उपलब्ध) दिवसाच्या तुलनेत delta
    जोडतो — हाच खरा "reversal होतोय का" चा signal आहे, नुसता आजचा स्थिर
    आकडा नाही. आधीचा डेटा नसेल (पहिला run) तर trend='NEW' राहतो.
    """
    prev_map = {s["sector"]: s for s in (previous_digest or {}).get("sectors", [])}

    for s in sector_results:
        prev = prev_map.get(s["sector"])
        if prev:
            score_change = round(s["avg_quant_score"] - prev["avg_quant_score"], 1)
            reversal_change = round(s["reversal_pct"] - prev["reversal_pct"], 1)
            s["score_change"] = score_change
            s["reversal_pct_change"] = reversal_change
            if score_change > 2:
                s["trend"] = "UP"
            elif score_change < -2:
                s["trend"] = "DOWN"
            else:
                s["trend"] = "FLAT"
        else:
            s["score_change"] = None
            s["reversal_pct_change"] = None
            s["trend"] = "NEW"
    return sector_results


def _prune_old_history():
    """History फोल्डर अनिश्चित काळ वाढू नये म्हणून जुन्या (३० दिवसांपेक्षा
    आधीच्या) snapshots काढून टाकतो."""
    if not os.path.isdir(HISTORY_DIR):
        return
    cutoff = date.today() - pd.Timedelta(days=HISTORY_RETENTION_DAYS)
    for fname in os.listdir(HISTORY_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            file_date = date.fromisoformat(fname.replace(".json", ""))
            if file_date < cutoff:
                os.remove(os.path.join(HISTORY_DIR, fname))
        except ValueError:
            continue


def generate_ai_commentary(sector_results: list) -> str:
    """
    Claude API वापरून वर्णनात्मक समालोचन — कुठलाही "खरेदी करा" सल्ला नाही,
    फक्त कुठे पॅटर्न दिसतोय याचं वर्णन. API key नसेल तर स्पष्ट संदेश
    (fake commentary कधीच नाही).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "⚠️ ANTHROPIC_API_KEY सेट नाही — AI समालोचन तयार करता आलं नाही (फक्त खालचा quant डेटा उपलब्ध)."

    if not sector_results:
        return "आज कुठल्याही sector साठी पुरेसा डेटा स्कॅन होऊ शकला नाही."

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        top5 = sector_results[:5]
        data_lines = []
        for s in top5:
            trend_note = ""
            if s.get("trend") == "UP":
                trend_note = f" (कालच्या तुलनेत सुधारणा: +{s['score_change']} score)"
            elif s.get("trend") == "DOWN":
                trend_note = f" (कालच्या तुलनेत घट: {s['score_change']} score)"
            elif s.get("trend") == "NEW":
                trend_note = " (तुलनेसाठी आधीचा डेटा उपलब्ध नाही)"
            data_lines.append(
                f"- {s['sector']}: {s['reversal_pct']}% स्टॉक्स Wyckoff breakout-pattern मध्ये, "
                f"{s['breakout_pct']}% स्टॉक्समध्ये confirmed price+volume breakout (किंमत resistance तोडून वर, "
                f"जास्त volume सह), {s['good_regime_pct']}% healthy-accumulation पॅटर्नमध्ये, सरासरी quant score "
                f"{s['avg_quant_score']}/100{trend_note} ({s['total_tickers_scanned']} tickers स्कॅन केले)"
            )
        data_summary = "\n".join(data_lines)

        prompt = f"""खालील आजच्या NSE micro-sector तांत्रिक स्कॅनचा सारांश आहे (delivery%, RSI, EMA,
Wyckoff phase यावर आधारित पॅटर्न-मॅचिंग स्कोअर, आणि कालच्या तुलनेत बदल — हे actual गुंतवणूक सल्ला नाही).

यावर आधारित जास्तीत जास्त १५० शब्दांचं, मराठी+इंग्रजी मिश्रित, वर्णनात्मक समालोचन लिही:
- कुठल्या sectors मध्ये सगळ्यात जास्त पॅटर्न-ब्रेडथ दिसतोय, आणि विशेषतः **कालच्या तुलनेत सुधारणा
  (UP trend)** दाखवणाऱ्या sectors ना जास्त महत्त्व दे — तोच खरा "आज नवीन काहीतरी घडतंय" चा संकेत
- "खरेदी करा" किंवा कुठलीही थेट कृती-सूचना (recommendation) अजिबात देऊ नकोस — फक्त निरीक्षण/वर्णन
- शेवटी एका ओळीत स्पष्ट लिही की हे केवळ ऐतिहासिक डेटा-पॅटर्न विश्लेषण आहे, गुंतवणूक सल्ला नाही

डेटा:
{data_summary}
"""
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        print(f"[DailyScan] AI commentary failed: {e}")
        return f"⚠️ AI समालोचन तयार करता आलं नाही: {e}"


def save_digest(sector_results: list, commentary: str) -> dict:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)

    digest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now().isoformat(),
        "generated_date": date.today().isoformat(),
        "ai_commentary": commentary,
        "sectors": sector_results,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)

    # History मध्येही तारीख-नावाने copy ठेवतो — उद्याच्या trend comparison साठी
    history_path = os.path.join(HISTORY_DIR, f"{digest['generated_date']}.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)

    _prune_old_history()

    print(f"[DailyScan] Digest saved -> {OUTPUT_FILE} (+ history archive)")
    return digest


def _send_email(subject: str, html_body: str, attachment_bytes: bytes = None, attachment_filename: str = None) -> bool:
    """Generic SMTP sender — daily digest, failure-alert, आणि breakout PDF alerts तिन्ही हेच वापरतात."""
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_APP_PASSWORD")
    recipient = os.environ.get("EMAIL_RECIPIENT")

    if not all([sender, password, recipient]):
        print("[DailyScan] Email credentials सेट नाहीत — ईमेल वगळला.")
        return False

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    body_part = MIMEMultipart("alternative")
    body_part.attach(MIMEText(html_body, "html"))
    msg.attach(body_part)

    if attachment_bytes is not None and attachment_filename:
        pdf_part = MIMEApplication(attachment_bytes, _subtype="pdf")
        pdf_part.add_header("Content-Disposition", "attachment", filename=attachment_filename)
        msg.attach(pdf_part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        print(f"[DailyScan] Email पाठवला -> {recipient} ({subject})")
        return True
    except Exception as e:
        print(f"[DailyScan] Email पाठवताना अडचण: {e}")
        return False


def send_email_digest(digest: dict) -> bool:
    """Gmail SMTP (App Password) वापरून डायजेस्ट ईमेल करतो."""
    trend_symbol = {"UP": "🟢 ▲", "DOWN": "🔴 ▼", "FLAT": "⚪ ―", "NEW": "🆕"}
    top_sectors_html = ""
    for s in digest["sectors"][:8]:
        symbol = trend_symbol.get(s.get("trend"), "")
        top_sectors_html += (
            f"<tr><td>{s['sector']}</td><td>{s['reversal_pct']}%</td>"
            f"<td>{s['good_regime_pct']}%</td><td>{s['avg_quant_score']}/100</td>"
            f"<td>{symbol}</td></tr>"
        )

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;">
    <h2>🏆 Alpha Quant — Daily Sector Digest ({digest['generated_date']})</h2>
    <div style="background:#ebf8ff; padding:15px; border-left:4px solid #3182ce; margin:15px 0;">
        {digest['ai_commentary'].replace(chr(10), '<br>')}
    </div>
    <table border="1" cellpadding="8" style="border-collapse:collapse; width:100%;">
        <tr style="background:#1a365d; color:white;">
            <th>Sector</th><th>Breakout %</th><th>Healthy-Accumulation %</th><th>Avg Score</th><th>कालच्या तुलनेत</th>
        </tr>
        {top_sectors_html}
    </table>
    <p style="font-size:11px; color:#718096; margin-top:20px;">
        ⚠️ हा रिपोर्ट केवळ ऐतिहासिक डेटा-पॅटर्न विश्लेषण आहे, SEBI-नोंदणीकृत गुंतवणूक सल्ला नाही.
    </p>
    </body></html>
    """
    return _send_email(f"Alpha Quant Daily Digest — {digest['generated_date']}", html_body)


def send_failure_alert(error_message: str):
    """
    Scan fail झालं (किंवा sanity-check मध्ये अडकलं) की हे वेगळं,
    त्वरित ओळखता येणारं alert-email पाठवतो — जेणेकरून तुम्हाला "आज
    रिपोर्टच आला नाही" हे लगेच कळेल, उगाच जुना/चुकीचा digest बघत बसू नये.
    """
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;">
    <h2 style="color:#e53e3e;">⚠️ Alpha Quant Daily Scan — FAILED</h2>
    <p>आजचा ({date.today().isoformat()}) daily sector scan पूर्ण होऊ शकला नाही.</p>
    <pre style="background:#f7fafc; padding:10px; border-radius:4px;">{error_message}</pre>
    <p>GitHub repo च्या Actions टॅबमध्ये संपूर्ण log बघा.</p>
    </body></html>
    """
    _send_email(f"⚠️ Alpha Quant Scan FAILED — {date.today().isoformat()}", html_body)


class ScanDegradedError(Exception):
    """Scan तांत्रिकदृष्ट्या 'यशस्वी' झाला पण निकाल संशयास्पद आहेत तेव्हा
    (उदा. जवळपास सगळे sectors/tickers स्किप झाले) — यामुळे असा अर्धवट/
    चुकीचा डेटा "आजची खरी परिस्थिती" म्हणून digest मध्ये जात नाही."""
    pass


def _sanity_check(sector_results: list, total_tickers_scanned: int):
    if len(sector_results) < MIN_SECTORS_FOR_HEALTHY_SCAN:
        raise ScanDegradedError(
            f"फक्त {len(sector_results)} sectors स्कॅन झाले (किमान {MIN_SECTORS_FOR_HEALTHY_SCAN} अपेक्षित). "
            "NSE/Yahoo Finance दोन्ही एकाच वेळी अनुपलब्ध असण्याची शक्यता आहे."
        )
    if total_tickers_scanned < MIN_TICKERS_FOR_HEALTHY_SCAN:
        raise ScanDegradedError(
            f"फक्त {total_tickers_scanned} tickers स्कॅन झाले (किमान {MIN_TICKERS_FOR_HEALTHY_SCAN} अपेक्षित). "
            "डेटा स्त्रोतात व्यापक अडचण असू शकते."
        )


MAX_ALERT_PDFS_PER_DAY = 5  # खर्च/वेळ मर्यादित ठेवण्यासाठी — जास्त signals आले तरी रोज जास्तीत जास्त इतकेच PDF


def _collect_alert_tickers(sector_results: list) -> list:
    """
    sector_results च्या top_tickers मधून दोन प्रकारचे alert-worthy tickers
    गोळा करतो: (१) confirmed price+volume breakout, (२) आजच झालेला Supertrend
    trend-flip (bullish किंवा bearish दोन्ही). एकाच ticker ला दोन्ही सिग्नल्स
    एकाच वेळी असतील तर तोही धरला जातो (त्याचं महत्त्व जास्त).
    """
    alert_list = []
    for s in sector_results:
        for t in s.get("top_tickers", []):
            triggers = []
            if t.get("is_breakout"):
                triggers.append("PRICE_VOLUME_BREAKOUT")
            if t.get("supertrend_flipped"):
                triggers.append(f"SUPERTREND_{t.get('supertrend_direction', 'FLIP')}")
            if triggers:
                alert_list.append({
                    "ticker": t["ticker"], "sector": s["sector"], "score": t["score"], "triggers": triggers,
                })
    alert_list.sort(key=lambda x: (len(x["triggers"]), x["score"]), reverse=True)  # दोन्ही triggers असलेले आधी
    return alert_list[:MAX_ALERT_PDFS_PER_DAY]


def generate_and_send_breakout_reports(sector_results: list):
    """
    आज ज्या tickers नी (अ) confirmed price+volume breakout, किंवा (ब) Daily
    Supertrend trend-flip (bullish/bearish) दाखवला, त्यांचा पूर्ण PDF रिपोर्ट
    (chart + fundamentals + news सकट, आपल्या existing PDF इंजिनने) बनवून
    Email attachment आणि Telegram दोन्हीवर पाठवतो.
    कुठलाही signal नसेल तर काहीच पाठवत नाही (रोज उगाच स्पॅम नको).
    """
    alert_list = _collect_alert_tickers(sector_results)
    if not alert_list:
        print("[DailyScan] आज कुठलाही breakout/supertrend-flip सिग्नल नाही — PDF alerts वगळले.")
        return

    print(f"[DailyScan] {len(alert_list)} alert tickers साठी PDF रिपोर्ट्स तयार करत आहे...")

    import report_pdf_generator
    import chart_builder
    import investment_fundamental as fund
    import investment_macro as macro
    import investment_news as news
    import data_provider
    import telegram_notifier

    TRIGGER_LABELS = {
        "PRICE_VOLUME_BREAKOUT": "🚀 Price+Volume Breakout",
        "SUPERTREND_BULLISH": "📈 Supertrend Bullish Flip",
        "SUPERTREND_BEARISH": "📉 Supertrend Bearish Flip",
    }

    for item in alert_list:
        ticker, sector, triggers = item["ticker"], item["sector"], item["triggers"]
        try:
            to_date = date.today()
            from_date = to_date.replace(year=to_date.year - 5)
            df_raw = data_provider.get_ohlc_data(ticker, from_date, to_date, active_broker=None)
            df_raw["Date"] = pd.to_datetime(df_raw["Date"])
            # Daily timeframe — Supertrend flip हा daily वरच calculate झालेला असतो;
            # breakout साठी सुद्धा Daily वापरतो जेणेकरून दोन्ही सिग्नल्स एकाच chart/analysis मधून सुसंगत दिसतील
            analysis = tech.run_advanced_technical_analysis(df_raw, "Daily (दैनिक)", None)
            if analysis["status"] != "SUCCESS":
                print(f"[DailyScan] {ticker}: PDF साठी पुरेसा डेटा नाही, वगळत आहे.")
                continue

            chart_fig = chart_builder.build_technical_chart(analysis["chart_data"], analysis, ticker, "Daily (दैनिक)")
            fundamental_result = fund.run_advanced_fundamental_analysis(ticker)
            quarterly_rows = fund.get_quarterly_earnings_table(ticker, n_quarters=6)
            crude, dxy, narrative = macro.fetch_global_commodity_trends()
            news_items = news.get_news_for_ticker(ticker, max_items=6)

            pdf_bytes = report_pdf_generator.build_stock_report_pdf(
                ticker=ticker, sector=sector, analysis=analysis,
                fundamental_result=fundamental_result, quarterly_rows=quarterly_rows,
                macro_data={"crude_oil_price": crude, "dollar_index_dxy": dxy, "narrative": narrative},
                chart_fig=chart_fig, news_items=news_items,
            )

            trigger_lines = "\n".join(f"• {TRIGGER_LABELS.get(t, t)}" for t in triggers)
            breakout_info = analysis.get("breakout") or {}
            supertrend_info = analysis.get("supertrend") or {}

            detail_lines = []
            if "PRICE_VOLUME_BREAKOUT" in triggers:
                detail_lines.append(
                    f"Breakout: Resistance ₹{breakout_info.get('resistance_level')} तुटली, "
                    f"सध्याची किंमत ₹{breakout_info.get('current_close')}, Volume {breakout_info.get('volume_ratio')}x सरासरी"
                )
            if any(t.startswith("SUPERTREND") for t in triggers):
                detail_lines.append(
                    f"Supertrend: {supertrend_info.get('current_trend')} trend कडे flip, "
                    f"Supertrend level ₹{supertrend_info.get('supertrend_value')}, Close ₹{supertrend_info.get('close')}"
                )

            subject_tags = " + ".join(TRIGGER_LABELS.get(t, t).split(" ", 1)[-1] for t in triggers)
            caption = (
                f"{trigger_lines}\n\n{ticker} ({sector})\nQuant Score: {analysis['score']}/100\n\n"
                + "\n".join(detail_lines)
                + "\n\n⚠️ हे ऐतिहासिक data-pattern विश्लेषण आहे, गुंतवणूक सल्ला नाही."
            )
            html_body = f"<pre style='font-family:Arial,sans-serif; white-space:pre-wrap;'>{caption}</pre><p>पूर्ण PDF रिपोर्ट सोबत जोडलाय.</p>"

            filename = f"{ticker}_alert_report_{date.today().isoformat()}.pdf"
            _send_email(
                subject=f"🔔 Signal Alert: {ticker} ({sector}) — {subject_tags}",
                html_body=html_body,
                attachment_bytes=pdf_bytes, attachment_filename=filename,
            )
            telegram_notifier.send_document(pdf_bytes, filename, caption=caption)

        except Exception as e:
            print(f"[DailyScan] {ticker} साठी alert PDF तयार/पाठवता आला नाही: {e}")
            continue


def run_daily_agent(max_tickers_per_sector: int = None, force: bool = False, smoke_test: bool = False) -> dict:
    """
    smoke_test=True: फक्त कनेक्टिव्हिटी तपासण्यासाठी — मोजक्याच sectors/tickers
    (max_tickers_per_sector खाली सेट होतं), holiday-check/sanity-check/email
    सगळं वगळतं, आणि JSON commit साठी वेगळी फाईल (history/commit होत नाही) —
    संपूर्ण १०० tickers स्कॅन होण्याची वाट न बघता NSE/Yahoo/Claude खरंच
    उपलब्ध आहेत की नाही हे पटकन तपासता येतं.
    """
    if not smoke_test:
        is_holiday, holiday_name = is_nse_trading_holiday()
        if is_holiday and not force:
            print(f"[DailyScan] आज NSE सुट्टी आहे ({holiday_name}) — स्कॅन वगळला. (force=True ने override करता येतं)")
            return {"skipped": True, "reason": f"NSE holiday: {holiday_name}"}

    print("[DailyScan] संपूर्ण मार्केट स्कॅन सुरू..." if not smoke_test else "[DailyScan] 🧪 SMOKE TEST मोड — मर्यादित स्कॅन...")
    sector_results = scan_all_sectors(max_tickers_per_sector=max_tickers_per_sector)
    total_tickers = sum(s["total_tickers_scanned"] for s in sector_results)
    print(f"[DailyScan] {len(sector_results)} sectors, एकूण {total_tickers} tickers स्कॅन झाले.")

    if smoke_test:
        commentary = generate_ai_commentary(sector_results)
        print("\n[DailyScan] 🧪 SMOKE TEST निकाल (काहीही सेव्ह/ईमेल केलं नाही):")
        print(f"  Sectors: {[s['sector'] for s in sector_results]}")
        print(f"  AI commentary preview: {commentary[:200]}...")
        return {"smoke_test": True, "sectors": sector_results, "ai_commentary": commentary}

    # Sanity check — इथे राईज झालं की खाली except मध्ये अडकून failure-alert जाईल
    _sanity_check(sector_results, total_tickers)

    previous_digest = _load_previous_digest()
    sector_results = compute_trend(sector_results, previous_digest)

    commentary = generate_ai_commentary(sector_results)
    digest = save_digest(sector_results, commentary)
    send_email_digest(digest)
    generate_and_send_breakout_reports(sector_results)
    print("[DailyScan] पूर्ण.")
    return digest


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Daily Sector Scan Agent")
    parser.add_argument("--smoke-test", action="store_true",
                         help="फक्त १ sector/२ tickers वर पटकन connectivity टेस्ट — काहीही सेव्ह/ईमेल होत नाही")
    parser.add_argument("--force", action="store_true",
                         help="NSE holiday असूनही स्कॅन जबरदस्तीने चालवा")
    args = parser.parse_args()

    try:
        if args.smoke_test:
            run_daily_agent(max_tickers_per_sector=2, smoke_test=True)
        else:
            result = run_daily_agent(force=args.force)
            if result.get("skipped"):
                pass  # सुट्टीमुळे वगळलं — हा failure नाही, exit code 0 च राहतो
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        print(f"[DailyScan] ❌ FATAL: {error_msg}")
        if not args.smoke_test:
            send_failure_alert(error_msg)
        raise SystemExit(1)  # GitHub Actions ला job 'failed' दाखवण्यासाठी
