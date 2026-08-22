"""
Full Stock Research Report -> PDF, reportlab (Platypus) वापरून.

Usage:
    from report_pdf_generator import build_stock_report_pdf
    pdf_bytes = build_stock_report_pdf(
        ticker, sector, analysis, fundamental_result, quarterly_rows,
        macro_data, chart_fig,
    )
"""

import io
import os
import re
from xml.sax.saxutils import escape
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---- Devanagari (मराठी) support ----
# Noto Sans Devanagari मध्ये फक्त देवनागरी glyphs आहेत, Latin/English नाहीत.
# म्हणून पूर्ण पॅराग्राफला हाच फॉन्ट दिला तर इंग्रजी शब्द रिकामे दिसतात.
# उपाय: base फॉन्ट Helvetica (पूर्ण Latin support) ठेवायचा, आणि text मधले
# फक्त देवनागरी भाग <font name="NotoDevanagari"> ने wrap करायचे (mixed_font_markup).
_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_DEVANAGARI_FONT = "NotoDevanagari"

try:
    pdfmetrics.registerFont(TTFont(_DEVANAGARI_FONT, os.path.join(_FONT_DIR, "NotoSansDevanagari-Regular.ttf")))
    _DEVANAGARI_AVAILABLE = True
except Exception as e:
    print(f"[report_pdf_generator] Devanagari font load failed, मराठी मजकूर PDF मध्ये नीट दिसणार नाही: {e}")
    _DEVANAGARI_AVAILABLE = False

_DEVANAGARI_RANGE = re.compile(r"[\u0900-\u097F\uA8E0-\uA8FF]+")


def mixed_font_markup(text: str) -> str:
    """Devanagari आणि Latin मिक्स असलेला मजकूर reportlab Paragraph मध्ये
    व्यवस्थित दिसण्यासाठी — Devanagari भागांना वेगळ्या फॉन्टमध्ये wrap करतो.
    (plain text साठी — आधी XML-escape करतो.)"""
    if not text:
        return text
    safe = escape(text)
    if not _DEVANAGARI_AVAILABLE:
        return safe
    return _DEVANAGARI_RANGE.sub(lambda m: f'<font name="{_DEVANAGARI_FONT}">{m.group(0)}</font>', safe)


def mixed_font_markup_raw(html_text: str) -> str:
    """आधीच <b>, <br/> सारखे reportlab markup tags असलेल्या (hand-written,
    trusted) strings साठी — escape करत नाही, फक्त Devanagari भाग wrap करतो."""
    if not html_text or not _DEVANAGARI_AVAILABLE:
        return html_text
    return _DEVANAGARI_RANGE.sub(lambda m: f'<font name="{_DEVANAGARI_FONT}">{m.group(0)}</font>', html_text)

NAVY = colors.HexColor("#1a365d")
BLUE = colors.HexColor("#3182ce")
LIGHT_BLUE = colors.HexColor("#ebf8ff")
RED = colors.HexColor("#e53e3e")
GREEN = colors.HexColor("#2f855a")
GREY = colors.HexColor("#718096")


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("ReportTitle", parent=styles["Title"], textColor=NAVY, fontSize=20))
    styles.add(ParagraphStyle("SectionHeading", parent=styles["Heading2"], textColor=NAVY, spaceBefore=14, spaceAfter=6))
    styles.add(ParagraphStyle("SubText", parent=styles["Normal"], textColor=GREY, fontSize=9))
    styles.add(ParagraphStyle("BodyJustify", parent=styles["Normal"], alignment=4, leading=14))
    styles.add(ParagraphStyle("DisclaimerStyle", parent=styles["Normal"], fontSize=8, textColor=GREY, leading=11))
    return styles


def _chart_image_flowable(chart_fig, max_width=17 * cm):
    """Plotly figure -> PNG bytes (kaleido) -> reportlab Image flowable."""
    try:
        png_bytes = chart_fig.to_image(format="png", width=1400, height=800, scale=2, engine="kaleido")
    except Exception as e:
        return Paragraph(mixed_font_markup(f"[!] Chart image तयार करता आला नाही: {e}"), getSampleStyleSheet()["Normal"])
    img_buf = io.BytesIO(png_bytes)
    img = Image(img_buf)
    aspect = img.imageHeight / float(img.imageWidth)
    img.drawWidth = max_width
    img.drawHeight = max_width * aspect
    return img


def build_stock_report_pdf(
    ticker: str,
    sector: str,
    analysis: dict,
    fundamental_result: dict,
    quarterly_rows: list,
    macro_data: dict,
    chart_fig=None,
    news_items: list = None,
) -> bytes:
    """
    सगळे argument आधीच dashboard मध्ये compute झालेले dict/list आहेत —
    हे function फक्त त्यांना professional PDF layout मध्ये टाकतं, नवीन
    calculation करत नाही (एकच source of truth — dashboard वर जे दिसतं तेच PDF मध्ये).
    """
    styles = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )
    story = []
    current_date_str = datetime.now().strftime("%d-%b-%Y")

    # ---------------- Cover ----------------
    story.append(Paragraph("ALPHA QUANT — STOCK RESEARCH REPORT", styles["ReportTitle"]))
    story.append(Paragraph(f"{ticker}  |  {sector}", styles["Heading3"]))
    story.append(Paragraph(f"Generated: {current_date_str}", styles["SubText"]))
    story.append(HRFlowable(width="100%", color=BLUE, thickness=1, spaceBefore=8, spaceAfter=14))

    # ---------------- Executive Summary ----------------
    story.append(Paragraph("Executive Summary (Data-Pattern Observation)", styles["SectionHeading"]))
    score = analysis.get("score", "N/A")
    regime = str(analysis.get("regime", "N/A")).replace("_", " ")
    reason = analysis.get("reason", "")
    summary_table = Table(
        [
            ["Quant Score", f"{score}/100"],
            ["Regime (Pattern)", regime],
            ["Market Gate (NIFTY proxy)", str(analysis.get("market_gate", "N/A")).replace("_", " ")],
            ["Wyckoff Phase", str(analysis.get("wyckoff_phase", "N/A")).split(" (")[0]],
            ["15-Day Avg Delivery %", f"{analysis.get('delivery_15d', 0):.1f}%"],
        ],
        colWidths=[6 * cm, 10 * cm],
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))
    story.append(Paragraph(mixed_font_markup(reason), styles["BodyJustify"]))

    # ---------------- Chart ----------------
    if chart_fig is not None:
        story.append(PageBreak())
        story.append(Paragraph("Technical Chart", styles["SectionHeading"]))
        story.append(_chart_image_flowable(chart_fig))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            mixed_font_markup(
                "[Blue] Fair Value Gap (FVG) | [Red] Swing High | [Green] Swing Low — "
                "हे ऐतिहासिक data-pattern मार्कर्स आहेत, ट्रेडिंग सिग्नल नाहीत."
            ),
            styles["SubText"],
        ))

    # ---------------- Fundamentals ----------------
    story.append(PageBreak())
    story.append(Paragraph("Fundamental Snapshot", styles["SectionHeading"]))
    fr = fundamental_result or {}

    def _fmt(v, suffix=""):
        return f"{v}{suffix}" if v is not None else "N/A"

    fund_table = Table(
        [
            ["Fundamental Score", f"{fr.get('fundamental_score', 'N/A')}/100"],
            ["PE Ratio", _fmt(round(fr["pe_ratio"], 1) if fr.get("pe_ratio") else None)],
            ["ROE", _fmt(round(fr["roe"], 1) if fr.get("roe") is not None else None, "%")],
            ["Debt/Equity", _fmt(round(fr["debt_to_equity"], 2) if fr.get("debt_to_equity") is not None else None)],
            ["Free Cash Flow", fr.get("free_cash_flow", "N/A")],
            ["Sales CAGR", _fmt(round(fr["sales_growth_3y"] * 100, 1) if fr.get("sales_growth_3y") is not None else None, "%")],
            ["Profit CAGR", _fmt(round(fr["profit_growth_3y"] * 100, 1) if fr.get("profit_growth_3y") is not None else None, "%")],
        ],
        colWidths=[6 * cm, 10 * cm],
    )
    fund_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(fund_table)
    story.append(Paragraph(f"Source: {fr.get('data_source', 'N/A')}", styles["SubText"]))

    # ---------------- Quarterly Earnings ----------------
    story.append(Spacer(1, 14))
    story.append(Paragraph("Quarterly Earnings (Sales & Net Profit)", styles["SectionHeading"]))
    if quarterly_rows:
        header = ["Quarter", "Sales (Rs. Cr)", "Net Profit (Rs. Cr)", "QoQ Sales Growth %"]
        rows = [header]
        for r in quarterly_rows:
            growth = r.get("qoq_growth_pct")
            rows.append([
                r.get("quarter", "N/A"),
                f"{r.get('sales_cr', 0):,.0f}",
                f"{r.get('profit_cr', 0):,.0f}" if r.get("profit_cr") is not None else "N/A",
                f"{growth:+.1f}%" if growth is not None else "N/A",
            ])
        earn_table = Table(rows, colWidths=[4 * cm, 4 * cm, 4.5 * cm, 4.5 * cm])
        earn_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(earn_table)
        story.append(Paragraph("Source: Yahoo Finance (live)", styles["SubText"]))
    else:
        story.append(Paragraph(mixed_font_markup("[!] या ticker साठी तिमाही earnings डेटा सध्या उपलब्ध नाही."), styles["Normal"]))

    # ---------------- Macro Context ----------------
    story.append(Spacer(1, 14))
    story.append(Paragraph("Macro Context", styles["SectionHeading"]))
    md = macro_data or {}
    crude = md.get("crude_oil_price")
    dxy = md.get("dollar_index_dxy")
    story.append(Paragraph(
        f"Crude Oil (WTI): {f'${crude:.2f}' if crude else 'N/A'}  |  "
        f"Dollar Index (DXY): {f'{dxy:.2f}' if dxy else 'N/A'}",
        styles["Normal"],
    ))
    if md.get("narrative"):
        story.append(Paragraph(mixed_font_markup_raw(md["narrative"].replace("\n", "<br/>")), styles["BodyJustify"]))

    # ---------------- News & Sentiment ----------------
    story.append(Spacer(1, 14))
    story.append(Paragraph("Recent News & Sentiment (Keyword-based, not ML)", styles["SectionHeading"]))
    if news_items:
        sentiment_tag = {"POSITIVE": "[+]", "NEGATIVE": "[-]", "NEUTRAL": "[~]"}
        for n in news_items[:8]:
            tag = sentiment_tag.get(n.get("label"), "[~]")
            line = f"{tag} {n.get('title', '')}  —  {n.get('source', '')}"
            story.append(Paragraph(mixed_font_markup(line), styles["Normal"]))
            story.append(Spacer(1, 2))
    else:
        story.append(Paragraph(mixed_font_markup("[!] सध्या संबंधित बातम्या उपलब्ध नाहीत."), styles["Normal"]))

    # ---------------- Disclaimer ----------------
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#cbd5e0"), thickness=0.5))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        mixed_font_markup_raw(
            "<b>Disclaimer:</b> हा रिपोर्ट केवळ शैक्षणिक/माहितीच्या उद्देशाने ऐतिहासिक डेटा-पॅटर्न विश्लेषणावर "
            "आधारित आहे. हा SEBI-नोंदणीकृत गुंतवणूक सल्ला नाही (Not SEBI Registered Investment/Research Advice), "
            "आणि यामधील कुठलाही मजकूर खरेदी/विक्रीची शिफारस मानू नये. गुंतवणुकीचे निर्णय घेण्यापूर्वी स्वतःचं संशोधन "
            "करा किंवा SEBI-नोंदणीकृत गुंतवणूक सल्लागाराचा सल्ला घ्या. बाजारातील गुंतवणूक जोखमीच्या अधीन आहे. "
            "डेटा स्त्रोत: NSE (jugaad-data) व Yahoo Finance — विलंबित/त्रुटीयुक्त असू शकतो."
        ),
        styles["DisclaimerStyle"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
