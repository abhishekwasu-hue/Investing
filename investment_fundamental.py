"""
Fundamental Analysis Engine — Research-institute दर्जाचं विश्लेषण.

महत्त्वाचा दृष्टिकोन: Yahoo Finance च्या summary `info` dict वर पूर्णपणे
अवलंबून राहत नाही (छोट्या/मिड-कॅप भारतीय स्टॉक्ससाठी हे अनेकदा अपुरं
असतं — PE/ROE/Debt सगळं N/A येऊ शकतं). त्याऐवजी शक्य तिथे raw financial
statements (balance sheet, income statement) मधून स्वतः ratios calculate
करतो — जास्त विश्वासार्ह, आणि institutional research सारखं.
"""

import pandas as pd
import yfinance as yf

CR = 1e7  # 1 Crore = 1,00,00,000


def _safe(d: dict, key: str):
    v = d.get(key) if d else None
    return v if v not in (None, "None", "") else None


def _to_cr(value):
    return round(value / CR, 1) if value is not None else None


def _pct(fraction):
    """0.224 -> 22.4 (Yahoo अनेक ratios fraction स्वरूपात देतो)"""
    return round(fraction * 100, 2) if fraction is not None else None


def _latest_col(df):
    """DataFrame चा सर्वात अलीकडचा (पहिला) कॉलम — annual statements मध्ये
    सर्वात नवीन वर्ष डावीकडे असतं."""
    if df is None or df.empty:
        return None
    return df.iloc[:, 0]


def _get_row(series, *possible_names):
    """Balance sheet/income statement मध्ये कंपनीनुसार row-नावं थोडी वेगळी
    असू शकतात (उदा. 'Total Debt' किंवा 'Long Term Debt' + 'Current Debt')
    — पहिलं जे सापडेल ते वापरतो."""
    if series is None:
        return None
    for name in possible_names:
        if name in series.index:
            val = series[name]
            if pd.notna(val):
                return float(val)
    return None


def _compute_from_statements(stock: "yf.Ticker") -> dict:
    """PE/ROE/Debt-Equity/Current Ratio raw financial statements मधून
    manually calculate करतो — Yahoo च्या summary info पेक्षा जास्त
    विश्वासार्ह (विशेषतः छोट्या भारतीय कंपन्यांसाठी)."""
    out = {"roe": None, "debt_to_equity": None, "current_ratio": None,
           "roa": None, "book_value_per_share": None}
    try:
        bs = _latest_col(stock.balance_sheet)
        inc = _latest_col(stock.income_stmt)

        equity = _get_row(bs, "Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest")
        total_debt = _get_row(bs, "Total Debt")
        if total_debt is None:
            ltd = _get_row(bs, "Long Term Debt") or 0
            std = _get_row(bs, "Current Debt", "Short Term Debt") or 0
            total_debt = ltd + std if (ltd or std) else None
        total_assets = _get_row(bs, "Total Assets")
        current_assets = _get_row(bs, "Current Assets")
        current_liabilities = _get_row(bs, "Current Liabilities")
        net_income = _get_row(inc, "Net Income")
        shares_out = _get_row(bs, "Ordinary Shares Number", "Share Issued")

        if total_debt is not None and equity not in (None, 0):
            out["debt_to_equity"] = round(total_debt / equity, 2)
        if current_assets is not None and current_liabilities not in (None, 0):
            out["current_ratio"] = round(current_assets / current_liabilities, 2)
        if net_income is not None and equity not in (None, 0):
            out["roe"] = round((net_income / equity) * 100, 2)
        if net_income is not None and total_assets not in (None, 0):
            out["roa"] = round((net_income / total_assets) * 100, 2)
        if equity is not None and shares_out not in (None, 0):
            out["book_value_per_share"] = round(equity / shares_out, 2)
    except Exception as e:
        print(f"[FUNDAMENTAL] statement-based ratio calc failed: {e}")
    return out


def run_advanced_fundamental_analysis(ticker: str) -> dict:
    """
    Real, बहु-आयामी fundamental screening — Valuation, Profitability,
    Financial Health, Growth, Cash Flow असं विभागलेलं.
    कुठलाही आकडा उपलब्ध नसेल तर fabricate न करता None/'N/A' — प्रामाणिकपणा
    accuracy पेक्षा जास्त महत्त्वाचा.
    """
    print(f"[FUNDAMENTAL] Fetching REAL financial ratios for: {ticker}")
    stock = yf.Ticker(ticker)

    try:
        info = stock.info or {}
    except Exception as e:
        print(f"[FUNDAMENTAL] info fetch failed for {ticker}: {e}")
        info = {}

    computed = _compute_from_statements(stock)

    # ---- Valuation ----
    pe_ratio = _safe(info, "trailingPE") or _safe(info, "forwardPE")
    if pe_ratio is None:
        # Fallback: किंमत / EPS स्वतः काढतो (info मध्ये PE नसेल तरी बरेचदा हे उपलब्ध असतं)
        eps = _safe(info, "trailingEps")
        price = _safe(info, "currentPrice") or _safe(info, "regularMarketPrice")
        if eps and price and eps > 0:
            pe_ratio = round(price / eps, 2)

    pb_ratio = _safe(info, "priceToBook")
    ev_ebitda = _safe(info, "enterpriseToEbitda")
    price_to_sales = _safe(info, "priceToSalesTrailing12Months")
    dividend_yield = _pct(_safe(info, "dividendYield"))
    market_cap_cr = _to_cr(_safe(info, "marketCap"))

    # ---- Profitability (info आधी, नाहीतर statements मधून calculated) ----
    roe = _pct(_safe(info, "returnOnEquity")) or computed["roe"]
    roa = _pct(_safe(info, "returnOnAssets")) or computed["roa"]
    operating_margin = _pct(_safe(info, "operatingMargins"))
    net_margin = _pct(_safe(info, "profitMargins"))
    gross_margin = _pct(_safe(info, "grossMargins"))

    # ---- Financial Health (info चा debtToEquity % स्वरूपात असतो — /100;
    # नाहीतर statements मधून calculated ratio थेट वापरतो) ----
    d2e_info = _safe(info, "debtToEquity")
    debt_to_equity = round(d2e_info / 100, 2) if d2e_info is not None else computed["debt_to_equity"]
    current_ratio = _safe(info, "currentRatio") or computed["current_ratio"]

    # ---- Growth ----
    sales_growth_3y, profit_growth_3y = _compute_cagr_growth(stock)

    # ---- Cash Flow ----
    fcf_raw = _safe(info, "freeCashflow")
    operating_cf_raw = _safe(info, "operatingCashflow")
    if fcf_raw is None:
        free_cash_flow_status = "N/A"
    else:
        free_cash_flow_status = "POSITIVE ✅" if fcf_raw > 0 else "NEGATIVE ⚠️"

    # ---- Composite score — जास्त factors, प्रत्येकाचं वजन लहान ----
    score = 40
    if sales_growth_3y is not None and sales_growth_3y >= 0.15: score += 10
    if profit_growth_3y is not None and profit_growth_3y >= 0.15: score += 10
    if debt_to_equity is not None and debt_to_equity <= 0.5: score += 12
    if roe is not None and roe >= 20.0: score += 10
    if operating_margin is not None and operating_margin >= 15.0: score += 8
    if current_ratio is not None and current_ratio >= 1.0: score += 5
    if free_cash_flow_status.startswith("POSITIVE"): score += 5

    return {
        "fundamental_score": min(max(score, 0), 100),
        # Valuation
        "market_cap_cr": market_cap_cr,
        "pe_ratio": pe_ratio,
        "pb_ratio": pb_ratio,
        "ev_ebitda": ev_ebitda,
        "price_to_sales": price_to_sales,
        "dividend_yield": dividend_yield,
        # Profitability
        "roe": roe,
        "roa": roa,
        "operating_margin": operating_margin,
        "net_margin": net_margin,
        "gross_margin": gross_margin,
        # Financial health
        "debt_to_equity": debt_to_equity,
        "current_ratio": current_ratio,
        "book_value_per_share": computed["book_value_per_share"],
        # Growth
        "sales_growth_3y": sales_growth_3y,
        "profit_growth_3y": profit_growth_3y,
        # Cash flow
        "free_cash_flow": free_cash_flow_status,
        "free_cash_flow_cr": _to_cr(fcf_raw),
        "operating_cf_cr": _to_cr(operating_cf_raw),
        "data_source": "Yahoo Finance (yfinance) — live + calculated from financial statements",
    }


def _compute_cagr_growth(stock: "yf.Ticker"):
    try:
        fin = stock.income_stmt
        if fin is None or fin.empty:
            return None, None
        revenue_row = fin.loc["Total Revenue"] if "Total Revenue" in fin.index else None
        profit_row = fin.loc["Net Income"] if "Net Income" in fin.index else None
        return _cagr_from_row(revenue_row), _cagr_from_row(profit_row)
    except Exception as e:
        print(f"[FUNDAMENTAL] growth calculation failed: {e}")
        return None, None


def _cagr_from_row(row):
    if row is None:
        return None
    row = row.dropna()
    if len(row) < 2:
        return None
    latest, oldest = row.iloc[0], row.iloc[-1]
    years = len(row) - 1
    if oldest <= 0 or latest <= 0 or years <= 0:
        return None
    return (latest / oldest) ** (1 / years) - 1


def get_quarterly_earnings_table(ticker: str, n_quarters: int = 6):
    """Real quarter-wise Sales & Net Profit (Rs. Cr) — Yahoo सहसा ४-५ तिमाहीच देतो."""
    stock = yf.Ticker(ticker)
    try:
        q = stock.quarterly_income_stmt
    except Exception as e:
        print(f"[FUNDAMENTAL] quarterly_income_stmt failed for {ticker}: {e}")
        return []

    if q is None or q.empty or "Total Revenue" not in q.index or "Net Income" not in q.index:
        return []

    revenue = q.loc["Total Revenue"]
    net_income = q.loc["Net Income"]
    cols = list(q.columns)[:n_quarters]

    rows = []
    prev_sales = None
    for col in reversed(cols):
        sales = revenue.get(col)
        if pd.isna(sales):
            continue
        profit = net_income.get(col)
        qoq_growth_pct = None
        if prev_sales not in (None, 0) and not pd.isna(prev_sales):
            qoq_growth_pct = (sales - prev_sales) / abs(prev_sales) * 100
        rows.append({
            "quarter": col.strftime("%b-%Y") if hasattr(col, "strftime") else str(col),
            "sales_cr": round(sales / CR, 1),
            "profit_cr": round(profit / CR, 1) if pd.notna(profit) else None,
            "qoq_growth_pct": round(qoq_growth_pct, 1) if qoq_growth_pct is not None else None,
        })
        prev_sales = sales
    return rows


def get_peer_comparison(tickers: list, max_peers: int = 8) -> list:
    """
    दिलेल्या tickers साठी (सहसा same micro-sector मधले) थोडक्यात
    comparison टेबल — PE, ROE, Debt/Equity, Fundamental Score.
    कुठला ticker fail झाला तर तो वगळतो, पूर्ण function crash होत नाही.
    """
    rows = []
    for t in tickers[:max_peers]:
        try:
            r = run_advanced_fundamental_analysis(t)
            rows.append({
                "Ticker": t,
                "Score": r["fundamental_score"],
                "PE": r["pe_ratio"],
                "ROE %": r["roe"],
                "Debt/Equity": r["debt_to_equity"],
                "Net Margin %": r["net_margin"],
            })
        except Exception as e:
            print(f"[FUNDAMENTAL] peer comparison failed for {t}: {e}")
    return rows
