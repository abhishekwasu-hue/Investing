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
    """
    PE/ROE/Debt-Equity/Current Ratio/ROCE/Working-Capital-Cycle raw
    financial statements मधून manually calculate करतो — Yahoo च्या summary
    info पेक्षा जास्त विश्वासार्ह (विशेषतः छोट्या भारतीय कंपन्यांसाठी).
    Screener.in जे दाखवतं त्यातले प्रमुख ratios इथे replicate केले आहेत.
    """
    out = {
        "roe": None, "debt_to_equity": None, "current_ratio": None,
        "roa": None, "book_value_per_share": None, "roce": None,
        "debtor_days": None, "inventory_days": None, "payable_days": None,
        "cash_conversion_cycle": None,
    }
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

        # ---- ROCE (Return on Capital Employed) — Screener.in चा सर्वात
        # आवडता profitability-quality metric. ROCE = EBIT / Capital Employed,
        # जिथे Capital Employed = Total Assets - Current Liabilities ----
        ebit = _get_row(inc, "EBIT", "Operating Income")
        if ebit is not None and total_assets is not None and current_liabilities is not None:
            capital_employed = total_assets - current_liabilities
            if capital_employed > 0:
                out["roce"] = round((ebit / capital_employed) * 100, 2)

        # ---- Working Capital Cycle — Screener.in मध्ये "Debtor Days",
        # "Inventory Days", "Days Payable" म्हणून दाखवतात ----
        revenue = _get_row(inc, "Total Revenue")
        cogs = _get_row(inc, "Cost Of Revenue", "Reconciled Cost Of Revenue")
        receivables = _get_row(bs, "Receivables", "Accounts Receivable", "Gross Accounts Receivable")
        inventory = _get_row(bs, "Inventory")
        payables = _get_row(bs, "Payables", "Accounts Payable", "Payables And Accrued Expenses")

        if receivables is not None and revenue not in (None, 0):
            out["debtor_days"] = round((receivables / revenue) * 365, 1)
        if inventory is not None and cogs not in (None, 0):
            out["inventory_days"] = round((inventory / cogs) * 365, 1)
        if payables is not None and cogs not in (None, 0):
            out["payable_days"] = round((payables / cogs) * 365, 1)
        if out["debtor_days"] is not None and out["inventory_days"] is not None and out["payable_days"] is not None:
            out["cash_conversion_cycle"] = round(out["debtor_days"] + out["inventory_days"] - out["payable_days"], 1)

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
    if computed["roce"] is not None and computed["roce"] >= 20.0: score += 8
    if operating_margin is not None and operating_margin >= 15.0: score += 5
    if current_ratio is not None and current_ratio >= 1.0: score += 5

    result = {
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
        "roce": computed["roce"],
        "operating_margin": operating_margin,
        "net_margin": net_margin,
        "gross_margin": gross_margin,
        # Financial health
        "debt_to_equity": debt_to_equity,
        "current_ratio": current_ratio,
        "book_value_per_share": computed["book_value_per_share"],
        # Working-capital cycle (Screener.in स्टाईल)
        "debtor_days": computed["debtor_days"],
        "inventory_days": computed["inventory_days"],
        "payable_days": computed["payable_days"],
        "cash_conversion_cycle": computed["cash_conversion_cycle"],
        # Growth
        "sales_growth_3y": sales_growth_3y,
        "profit_growth_3y": profit_growth_3y,
        # Cash flow
        "free_cash_flow": free_cash_flow_status,
        "free_cash_flow_cr": _to_cr(fcf_raw),
        "operating_cf_cr": _to_cr(operating_cf_raw),
        "data_source": "Yahoo Finance (yfinance) — live + calculated from financial statements",
    }
    result["pros"], result["cons"] = generate_pros_cons(result)
    return result


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


def generate_pros_cons(result: dict) -> tuple:
    """
    Screener.in च्या "Pros / Cons" सेक्शन सारखं — आधीच calculate केलेल्या
    ratios वरून साधे, पारदर्शक rule-based निरीक्षणं. कुठलाही नवीन डेटा
    आणत नाही, फक्त वरच्या numbers ना वाचनीय वाक्यांमध्ये मांडतं.
    ⚠️ हे निरीक्षणं आहेत, शिफारशी नाहीत — भाषा मुद्दाम तटस्थ ठेवलीये.
    """
    pros, cons = [], []

    de = result.get("debt_to_equity")
    if de is not None:
        if de <= 0.3:
            pros.append(f"कंपनीवर कमी कर्ज आहे (Debt/Equity: {de})")
        elif de >= 1.5:
            cons.append(f"कंपनीवर तुलनेने जास्त कर्ज आहे (Debt/Equity: {de})")

    roe = result.get("roe")
    if roe is not None:
        if roe >= 20:
            pros.append(f"चांगला Return on Equity — ROE: {roe}%")
        elif roe < 10:
            cons.append(f"तुलनेने कमी Return on Equity — ROE: {roe}%")

    roce = result.get("roce")
    if roce is not None:
        if roce >= 20:
            pros.append(f"भांडवलावर चांगला परतावा — ROCE: {roce}%")
        elif roce < 10:
            cons.append(f"भांडवलावर तुलनेने कमी परतावा — ROCE: {roce}%")

    sales_g = result.get("sales_growth_3y")
    if sales_g is not None:
        if sales_g >= 0.15:
            pros.append(f"सातत्यपूर्ण विक्री वाढ — Sales CAGR: {sales_g*100:.1f}%")
        elif sales_g < 0:
            cons.append(f"विक्रीत घट झालेली दिसते — Sales CAGR: {sales_g*100:.1f}%")

    profit_g = result.get("profit_growth_3y")
    if profit_g is not None and profit_g < 0:
        cons.append(f"नफ्यात घट झालेली दिसते — Profit CAGR: {profit_g*100:.1f}%")

    ccc = result.get("cash_conversion_cycle")
    if ccc is not None:
        if ccc <= 30:
            pros.append(f"कार्यक्षम Working Capital Cycle ({ccc} दिवस)")
        elif ccc >= 90:
            cons.append(f"Working Capital Cycle तुलनेने लांब आहे ({ccc} दिवस) — पैसे व्यवसायात जास्त काळ अडकतात")

    if result.get("free_cash_flow") == "POSITIVE ✅":
        pros.append("Free Cash Flow सकारात्मक आहे")
    elif result.get("free_cash_flow") == "NEGATIVE ⚠️":
        cons.append("Free Cash Flow सध्या नकारात्मक आहे")

    cr = result.get("current_ratio")
    if cr is not None and cr < 1.0:
        cons.append(f"Current Ratio 1 पेक्षा कमी आहे ({cr}) — अल्पकालीन तरलतेवर लक्ष ठेवावं")

    return pros, cons


def get_multi_year_financials(ticker: str, years: int = 5) -> list:
    """
    Screener.in च्या 'Profit & Loss' टेबलसारखं — वार्षिक Sales, Net Profit,
    Operating Margin % चा ट्रेंड (Yahoo सहसा ३-४ वर्षंच annual data देतो,
    Screener.in इतकी १०+ वर्षं खोली मोफत स्रोतातून मिळत नाही — ही एक
    प्रामाणिक मर्यादा आहे).
    """
    stock = yf.Ticker(ticker)
    try:
        inc = stock.income_stmt
    except Exception as e:
        print(f"[FUNDAMENTAL] annual financials fetch failed for {ticker}: {e}")
        return []

    if inc is None or inc.empty or "Total Revenue" not in inc.index:
        return []

    revenue = inc.loc["Total Revenue"]
    net_income = inc.loc["Net Income"] if "Net Income" in inc.index else None
    operating_income = inc.loc["Operating Income"] if "Operating Income" in inc.index else None

    cols = list(inc.columns)[:years]
    rows = []
    for col in reversed(cols):
        sales = revenue.get(col)
        if pd.isna(sales):
            continue
        profit = net_income.get(col) if net_income is not None else None
        op_income = operating_income.get(col) if operating_income is not None else None
        opm = round(float(op_income) / float(sales) * 100, 1) if (op_income is not None and pd.notna(op_income) and sales) else None
        rows.append({
            "year": col.strftime("%Y") if hasattr(col, "strftime") else str(col),
            "sales_cr": round(float(sales) / CR, 1),
            "net_profit_cr": round(float(profit) / CR, 1) if (profit is not None and pd.notna(profit)) else None,
            "opm_pct": opm,
        })
    return rows
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
