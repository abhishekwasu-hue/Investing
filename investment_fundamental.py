import pandas as pd
import yfinance as yf


def run_advanced_fundamental_analysis(ticker: str):
    """
    Real fundamental screening using Yahoo Finance data (via yfinance),
    replacing the previous hardcoded/mock numbers.

    NOTE: Yahoo's coverage of Indian mid/small-caps can have gaps or
    reporting-lag for some fields. Any field that isn't available comes
    back as None instead of a fabricated number, so the caller/UI can
    show 'N/A' honestly.
    """
    print(f"[FUNDAMENTAL] Fetching REAL financial ratios for: {ticker}")

    stock = yf.Ticker(ticker)
    try:
        info = stock.info or {}
    except Exception as e:
        print(f"[FUNDAMENTAL] Could not fetch info for {ticker}: {e}")
        info = {}

    pe_ratio = info.get("trailingPE") or info.get("forwardPE")

    # Yahoo reports debtToEquity as a percentage (e.g. 45.2 == 0.452 ratio)
    d2e_raw = info.get("debtToEquity")
    debt_to_equity = round(d2e_raw / 100, 3) if d2e_raw is not None else None

    roe_raw = info.get("returnOnEquity")  # fraction, e.g. 0.224
    roe = round(roe_raw * 100, 2) if roe_raw is not None else None

    fcf_raw = info.get("freeCashflow")
    if fcf_raw is None:
        free_cash_flow = "N/A"
    else:
        free_cash_flow = "POSITIVE ✅" if fcf_raw > 0 else "NEGATIVE ⚠️"

    sales_growth_3y, profit_growth_3y = _compute_cagr_growth(stock)

    fundamental_score = 50
    if sales_growth_3y is not None and sales_growth_3y >= 0.15:
        fundamental_score += 15
    if debt_to_equity is not None and debt_to_equity <= 0.5:
        fundamental_score += 20
    if roe is not None and roe >= 20.0:
        fundamental_score += 15

    return {
        "fundamental_score": min(max(fundamental_score, 0), 100),
        "pe_ratio": pe_ratio,
        "debt_to_equity": debt_to_equity,
        "roe": roe,
        "free_cash_flow": free_cash_flow,
        "sales_growth_3y": sales_growth_3y,
        "profit_growth_3y": profit_growth_3y,
        "data_source": "Yahoo Finance (yfinance) — live",
    }


def _compute_cagr_growth(stock: "yf.Ticker"):
    """3-year-ish CAGR for Revenue and Net Income from annual financials."""
    try:
        fin = stock.income_stmt  # annual statement, most recent column first
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
    latest = row.iloc[0]
    oldest = row.iloc[-1]
    years = len(row) - 1
    if oldest <= 0 or latest <= 0 or years <= 0:
        return None
    return (latest / oldest) ** (1 / years) - 1


def get_quarterly_earnings_table(ticker: str, n_quarters: int = 6):
    """
    Real quarter-wise Sales & Net Profit (in INR Crores) for the given
    ticker, pulled live from Yahoo Finance — replaces the previously
    hardcoded earnings_table_html numbers in investment_terminal.py.

    NOTE: Yahoo generally exposes only the last 4-5 reported quarters
    for Indian tickers, so n_quarters may return fewer rows than asked.
    """
    stock = yf.Ticker(ticker)
    try:
        q = stock.quarterly_income_stmt
    except Exception as e:
        print(f"[FUNDAMENTAL] quarterly_income_stmt failed for {ticker}: {e}")
        return []

    if q is None or q.empty:
        return []
    if "Total Revenue" not in q.index or "Net Income" not in q.index:
        return []

    revenue = q.loc["Total Revenue"]
    net_income = q.loc["Net Income"]
    cols = list(q.columns)[:n_quarters]

    rows = []
    prev_sales = None
    for col in reversed(cols):  # oldest -> latest, so QoQ growth is computable
        sales = revenue.get(col)
        if pd.isna(sales):
            continue
        profit = net_income.get(col)

        qoq_growth_pct = None
        if prev_sales not in (None, 0) and not pd.isna(prev_sales):
            qoq_growth_pct = (sales - prev_sales) / abs(prev_sales) * 100

        rows.append({
            "quarter": col.strftime("%b-%Y") if hasattr(col, "strftime") else str(col),
            "sales_cr": round(sales / 1e7, 1),                          # INR -> Crores
            "profit_cr": round(profit / 1e7, 1) if pd.notna(profit) else None,
            "qoq_growth_pct": round(qoq_growth_pct, 1) if qoq_growth_pct is not None else None,
        })
        prev_sales = sales

    return rows  # chronological order, oldest first
