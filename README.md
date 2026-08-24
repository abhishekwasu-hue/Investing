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
│   ├── 1_Technical_Chart.py
│   ├── 2_Fundamentals.py
│   ├── 3_Sector_Screener.py
│   ├── 4_Macro_News.py
│   └── 5_Upgrade_to_Pro.py
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


## 6. Daily AI Sector-Scan Agent

`daily_scan_agent.py` scans every micro-sector in `investment_master_mapping.csv`,
computes a "breadth" score per sector (% of tickers showing a Wyckoff
breakout pattern / healthy-accumulation regime), asks Claude to write a
short descriptive (never advisory) commentary, and saves everything to
`daily_reports/latest_digest.json` — which the in-app **Daily Digest**
page reads.

### How it runs automatically
`.github/workflows/daily_scan.yml` runs this on a GitHub Actions cron
schedule (weekdays, 4:30 PM IST by default — after NSE closes), commits
the updated `daily_reports/latest_digest.json` back to the repo, which
triggers Streamlit Cloud to auto-redeploy with the fresh digest. You can
also trigger it manually anytime from the repo's **Actions** tab →
"Daily Sector Scan" → **Run workflow**.

### Required GitHub Actions secrets
Set these under repo **Settings → Secrets and variables → Actions**
(NOT Streamlit Cloud secrets — this runs in GitHub's own environment):

```
ANTHROPIC_API_KEY     # Claude API key, from console.anthropic.com — required for AI commentary
EMAIL_SENDER          # Gmail address to send the daily digest from (optional — skips email if unset)
EMAIL_APP_PASSWORD    # Gmail App Password (not your normal password) — myaccount.google.com/apppasswords
EMAIL_RECIPIENT       # Where the daily digest email should go
```

Without `ANTHROPIC_API_KEY`, the scan still runs and the quant data still
saves — the AI commentary section just shows a clear "not configured"
message instead of fabricating one. Without the email secrets, email
sending is silently skipped (no crash) — the in-app Daily Digest page
still works either way.

### Testing it yourself
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python daily_scan_agent.py
```
This was tested end-to-end with mocked data (sector breadth aggregation,
JSON save/load round-trip, and graceful no-credentials fallbacks) — but
the actual Claude API call and email send could not be tested from the
build environment (no network access to api.anthropic.com or Gmail SMTP
from this sandbox). Verify both once with real credentials before relying
on it daily.

### Tier-1 Reliability additions (production-hardening)

The daily agent now includes:
- **`nse_holidays.py`** — skips the scan entirely on declared NSE trading
  holidays (2026 list included; update this file each January when NSE
  publishes the new year's calendar).
- **Retry with backoff** — each ticker gets up to 2 retries (3s apart)
  before being skipped, so a single transient NSE/Yahoo hiccup doesn't
  quietly degrade the day's data.
- **Sanity check** (`ScanDegradedError`) — if fewer than 5 sectors or 20
  tickers total get scanned successfully, the run is treated as *failed*
  (not published as "today's real reading") rather than silently showing
  a mostly-empty digest as if it were meaningful.
- **Failure alert email** — any fatal error (including the sanity check
  above) triggers a separate `⚠️ Alpha Quant Scan FAILED` email (uses the
  same `EMAIL_*` secrets) and exits with a non-zero code, so GitHub
  Actions marks the job as failed too.
- **Stale-digest warning in the app** — the Daily Digest page now counts
  *trading days* (skipping weekends/holidays) since the last successful
  scan and shows a red/yellow banner if it's 1-2+ days stale, instead of
  silently showing old data as if it were fresh.

All of the above was tested with mocked failures (simulated transient
errors, simulated total data-source outage, simulated holidays) — see the
conversation history for the exact test commands. The actual GitHub
Actions run, NSE/Yahoo/Claude/Gmail calls still need a real first run to
confirm end-to-end (untestable from the build sandbox, no network access
to those services).

### Tier-2 additions (trend + operational safety)

- **Day-over-day trend** — every daily scan is now archived to
  `daily_reports/history/YYYY-MM-DD.json` (auto-pruned after 30 days).
  Each sector gets a `trend` field (`UP`/`DOWN`/`FLAT`/`NEW`) and a
  `score_change` vs. the last available previous trading day. This is
  the actual "reversal happening" signal — a static snapshot alone
  can't show that. The Daily Digest page has a new "🚀 Most Improved
  Today" section, and the AI commentary prompt now includes the trend
  data so Claude's writeup emphasizes sectors improving day-over-day,
  not just sectors that happen to score high today.
- **Concurrency safety** — the workflow now uses a `concurrency` group
  so a manual "Run workflow" trigger and the scheduled run can never
  execute simultaneously (the later one queues instead of racing on the
  git push). A `git pull --rebase` before push is a second safety net.
- **Smoke-test mode** — `python daily_scan_agent.py --smoke-test` scans
  just 2 tickers per sector, skips the holiday/sanity checks, and
  **saves and emails nothing** — use this to quickly verify NSE/Yahoo/
  Claude connectivity from GitHub Actions ("Run workflow" → check the
  "smoke_test" box) without waiting for or polluting a full run.

Tested with mocked multi-day scans (trend correctly showed +13.5/UP and
-7.0/DOWN across two simulated days) and mocked smoke-test runs (confirmed
zero files written/emailed). The actual GitHub Actions concurrency
behavior and a real smoke-test against live NSE/Yahoo/Claude still need
verification with real credentials (untestable from this sandbox).

### Tier-3 additions (schema versioning + parallelization)

- **Schema versioning** — every digest now carries `schema_version` (currently
  2). `_load_previous_digest()` and the Daily Digest page both check it:
  a missing version is treated as the oldest format (v1, still readable),
  and a version *newer* than what the code knows about is safely skipped
  rather than mis-parsed. Corrupt JSON is also caught explicitly. Bump
  `SCHEMA_VERSION` in `daily_scan_agent.py` whenever you add/remove digest
  fields.
- **Parallelized scanning** — ticker fetches now run concurrently
  (`ThreadPoolExecutor`, since this is network I/O, not CPU work) instead
  of one-by-one. Default is 4 workers, tunable via the `SCAN_MAX_WORKERS`
  env var (or the `SCAN_MAX_WORKERS` repo Actions **variable** — Settings
  → Secrets and variables → Actions → Variables tab, not Secrets). Sector
  aggregation math stays sequential (it's cheap and this avoids any
  race-condition risk). **This is a genuine trade-off, not a free win** —
  more workers means more simultaneous requests from the same GitHub
  Actions IP, which raises the odds of NSE rate-limiting. If you start
  seeing more failures than before, lower `SCAN_MAX_WORKERS` (1 = fully
  sequential, same behavior as before this change).

Tested with a simulated 50ms-per-call delay: 4 workers gave a measured
2.1x speedup over sequential, and — critically — the aggregated sector
results were verified to be byte-for-byte identical between the
sequential and parallel runs (same sectors, same ticker counts), so the
concurrency doesn't change *what* gets reported, only how fast it's
computed. Real-world speedup/failure-rate against actual NSE/Yahoo still
needs to be observed over a few real days.

## 7. Breakout Alerts — PDF via Email + Telegram

When the daily scan finds tickers with a **confirmed price+volume breakout**
(see Tier-3 technical analysis section), it now automatically:
1. Generates the full stock research PDF (chart + fundamentals + news —
   same engine as the manual "Generate PDF Report" button) for up to
   `MAX_BREAKOUT_PDFS_PER_DAY` (default 5) top-scoring breakout tickers.
2. Emails each PDF as an attachment to `EMAIL_RECIPIENT`.
3. Sends each PDF as a Telegram document to `TELEGRAM_CHAT_ID`, via a bot.

**No breakout that day → nothing is sent** (no daily spam either way).

### Telegram setup
1. Message **@BotFather** on Telegram → `/newbot` → follow prompts → copy the bot token.
2. Send your new bot any message (or add it to a group/channel).
3. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser
   to find your `chat_id` (or the group's) in the response JSON.
4. Add to GitHub Actions secrets:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
   TELEGRAM_CHAT_ID=987654321
   ```

Without these two secrets, Telegram sending is silently skipped — email
(if configured) still works independently, and vice versa.

### Tested vs. not tested
Tested end-to-end with mocked data: breakout tickers are correctly
collected and ranked by score, a real PDF (~270KB, with chart) gets
generated and attached to the email MIME structure, and the Telegram
`sendDocument`/`sendMessage` payloads match Telegram's Bot API spec —
**but the actual live call to api.telegram.org could not be tested**
(no network access to Telegram from the build sandbox). Trigger the
workflow manually once with real credentials to confirm delivery.

### If you want this sent to multiple clients/subscribers
This currently sends to one `EMAIL_RECIPIENT` / one `TELEGRAM_CHAT_ID`
(you). Broadcasting to every Pro subscriber would need looping over the
`subscription.py` user list and collecting each person's email/Telegram
chat ID — a natural next step if you want this productized, but not
built yet.

## 8. Daily Supertrend Flip Alerts

`investment_technical.py` now computes a classic ATR-based **Supertrend**
(10-period ATR, 3x multiplier — standard settings) on Daily data, and
detects **trend flips** (bullish or bearish) — a flip only fires when
today's trend differs from yesterday's, not on every "still in uptrend"
day.

This plugs into the same breakout-alert pipeline from section 7 — a
ticker can now trigger a PDF+Email+Telegram alert for **either** a
confirmed price+volume breakout, a Supertrend flip, or both (tickers
with both signals are prioritized to the top). The alert PDF/caption
clearly labels which trigger(s) fired.

1-Hour intraday breakout detection was discussed but intentionally not
built yet — it requires a live broker connection (which the automated
GitHub Actions scan doesn't have) and runs into Upstox's daily
token-expiry problem for unattended runs. Revisit if/when a long-lived
Analytics Token or automated token-refresh is set up.

Tested with a synthetic 3-phase (up/down/up) price series: Supertrend
correctly stayed below price in uptrends and above price in downtrends,
flips were detected at the right transition points (with expected lag,
since it's a trend-following indicator by design), and the dual-trigger
prioritization + alert captions were verified end-to-end with mocked data.
