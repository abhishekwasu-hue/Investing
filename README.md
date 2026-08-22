# Alpha Quant Pro Terminal

NIFTY/NSE micro-sector स्टॉक स्क्रीनर आणि टेक्निकल-रिपोर्टिंग टर्मिनल, Streamlit वर बनवलेला.

## ⚠️ Important — before going live

Some modules currently return **hardcoded / random mock data** instead of real values,
and the app's core buy/sell signal depends on this data:

| File | Issue |
|---|---|
| `investment_database.py` | `No_of_Trades` & `Delivery_Pct` are `np.random.*` — not real NSE data |
| `investment_terminal.py` | Quarterly earnings table is static HTML, same for every ticker |
| `investment_fundamental.py` | PE / ROE / Debt-to-Equity are fixed `mock_` values for every ticker |
| `investment_macro.py` | NSDL FPI flows & commodity prices are hardcoded, not scraped |

**Do not use this for real trading decisions until these are replaced with real data sources**
(e.g. actual NSE bhavcopy/delivery data, real quarterly results from an API, live FPI data from NSDL).

## Project structure

```
.
├── investment_terminal.py       # Streamlit UI / entrypoint
├── investment_technical.py      # Technical analysis engine
├── investment_screener.py       # Price correction vs fall screener
├── investment_fundamental.py    # Fundamental scoring (currently mock)
├── investment_macro.py          # Macro/FPI narrative (currently mock)
├── investment_database.py       # One-time/offline data sync script (yfinance)
├── investment_master_mapping.csv
├── requirements.txt
└── investment_data_warehouse/   # generated CSVs — NOT committed to git
```

## 1. Run locally

```bash
pip install -r requirements.txt

# One-time: build the local data warehouse (takes a while, hits yfinance)
python investment_database.py

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

### ⚠️ Data warehouse problem on Cloud
`investment_terminal.py` reads CSVs from `investment_data_warehouse/`, but that folder
is not in git, so it won't exist on Streamlit Cloud. You need one of these:

- **Option A (simplest):** Add a one-time startup check in `investment_terminal.py` that
  calls `sync_universal_database()` from `investment_database.py` if the warehouse folder
  is empty — but syncing ~100 tickers via yfinance on every cold start will be slow and
  may hit rate limits.
- **Option B (recommended):** Run `investment_database.py` locally/on a scheduled GitHub
  Action, then upload the resulting CSVs to a cloud bucket (S3 / GCS / a private GitHub
  release) and have the app download only the CSVs it needs, on demand, cached.
- **Option C:** Use `st.cache_data` + fetch data live from `yfinance` directly inside the
  app instead of pre-building a local warehouse at all — simplest for a small ~100-ticker
  universe.

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

