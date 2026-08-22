# Alpha Quant Pro Terminal

NIFTY/NSE micro-sector स्टॉक स्क्रीनर आणि टेक्निकल-रिपोर्टिंग टर्मिनल, Streamlit वर बनवलेला.

## ✅ Current status

Real data throughout: NSE OHLC + Delivery% (`jugaad-data`, auto-fetched
on-demand), fundamentals + quarterly earnings (Yahoo Finance), macro
(crude/DXY live, FPI manual-CSV), and news+sentiment (RSS feeds,
keyword-based). Full multi-page dashboard, PDF research reports, login +
Free/Pro subscription with Razorpay checkout.

**Still not SEBI-registered investment advice** — the app deliberately uses
descriptive ("data-pattern observation") language rather than buy/sell
recommendations, and every report/page carries a disclaimer. See the
`## Login, Subscription & Payment Setup` section below before a public launch.

## Project structure

```
.
├── investment_terminal.py       # Entrypoint (Overview page) — login, subscription status, PDF button
├── app_state.py                 # Shared sidebar/session-state across all pages
├── data_provider.py             # Broker-agnostic facade (live broker OR free NSE data)
├── chart_builder.py             # Candlestick+RSI chart (shared by dashboard & PDF)
├── report_pdf_generator.py      # PDF research report engine (reportlab)
├── auth.py                      # Login/Register (streamlit-authenticator)
├── subscription.py              # Free/Pro tiers + daily usage limits (SQLite)
├── payments.py                  # Razorpay order + signature verification
├── investment_technical.py      # Technical analysis engine
├── investment_screener.py       # Price correction vs fall screener
├── investment_fundamental.py    # Fundamentals + quarterly earnings (Yahoo Finance)
├── investment_macro.py          # Crude/DXY (live) + FPI flows (manual CSV)
├── investment_news.py           # RSS news + keyword sentiment
├── investment_database.py       # NSE data sync (bulk + on-demand single-ticker)
├── investment_master_mapping.csv
├── requirements.txt
├── pages/
│   ├── 1_📈_Technical_Chart.py
│   ├── 2_📊_Fundamentals.py
│   ├── 3_🔍_Sector_Screener.py
│   ├── 4_📰_Macro_News.py
│   └── 5_💳_Upgrade_to_Pro.py
├── broker_adapters/              # Upstox / Zerodha / Angel One / Free-data — pluggable
├── fonts/                        # Noto Sans Devanagari (Marathi text in PDFs)
└── investment_data_warehouse/    # auto-generated CSVs — NOT committed to git
```

## 1. Run locally

```bash
pip install -r requirements.txt

# Data sync is now AUTOMATIC (on-demand, per ticker) — you don't need to run
# investment_database.py separately. It still exists if you want to
# pre-warm the entire universe in one go: python investment_database.py

# Launch the app
streamlit run investment_terminal.py
```

## 2. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: Alpha Quant Pro Terminal"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

`investment_data_warehouse/` is git-ignored on purpose — GitHub isn't meant to host
hundreds of per-ticker CSVs, and Streamlit Cloud rebuilds the environment fresh anyway.

## 3. Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in with GitHub.
2. **New app** → select your repo, branch `main`, main file path `investment_terminal.py`.
3. Deploy.

### Data warehouse on Cloud — SOLVED (on-demand auto-fetch)
`data_provider.py` / `broker_adapters/free_data_adapter.py` now fetch a
ticker's NSE data **on-demand, automatically**, the first time it's opened —
no separate script needs to run, on Cloud or locally. When a ticker is
requested and its CSV isn't in `investment_data_warehouse/` yet, the app
fetches it live from NSE right then (a few seconds), caches it to disk, and
every later visit for that ticker is instant. The Sector Screener does the
same per-ticker while it scans. `investment_database.py`'s bulk
`sync_universal_database()` still exists if you ever want to pre-warm the
whole universe in one go, but it's optional now.

### Secrets
If you later add a broker API key, DB credentials, etc., put them in Streamlit Cloud's
**App settings → Secrets** (TOML format) — never commit them. Access via `st.secrets["KEY"]`.

## 4. requirements.txt

Already present and Cloud-compatible (see the actual file for the complete,
up-to-date list — streamlit, plotly, pandas, numpy, yfinance, jugaad-data,
reportlab, kaleido, feedparser, streamlit-authenticator, bcrypt, razorpay).

## 5. Login, Subscription & Payment Setup (Public/Monetized launch)

The app now requires login (`auth.py`, streamlit-authenticator) and gates PDF
reports + Sector Screener behind a Free daily limit / Pro subscription
(`subscription.py`, SQLite) with Razorpay checkout (`payments.py`).

### Required environment variables / Streamlit secrets
```
RAZORPAY_KEY_ID=rzp_test_xxxx      # from https://dashboard.razorpay.com
RAZORPAY_KEY_SECRET=xxxx
```
Without these, the Upgrade page shows a clear "not configured" message —
the Free tier works fully without them.

### Before going live
1. Open `auth_config.yaml` (auto-created on first run) and change `cookie.key`
   to a random secret string.
2. **Never commit `auth_config.yaml` or `app_data.db`** — both are already in
   `.gitignore` (they contain hashed passwords / subscription data).
3. Test the full Razorpay flow in **Test Mode** (test API keys + Razorpay's
   test card numbers) before switching to live keys — this couldn't be
   tested end-to-end from the build environment since it has no network
   access to razorpay.com.
4. Streamlit Cloud's filesystem is ephemeral — `app_data.db` (subscriptions)
   and `auth_config.yaml` (user accounts) will reset on redeploy. For a real
   production launch, move both to a hosted database (e.g. Supabase/Postgres)
   instead of local SQLite/YAML.
5. Adjust `FREE_LIMITS` in `subscription.py` and `PRO_PLAN_PRICE_INR` in
   `payments.py` to whatever pricing you decide on.

