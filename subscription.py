"""
Subscription tiers (FREE / PRO) आणि daily usage limits — SQLite मध्ये track
होतात (हलकं, server लागत नाही, Streamlit Cloud वर सुद्धा काम करतं — फक्त
लक्षात ठेवा की Streamlit Cloud चा filesystem ephemeral आहे, म्हणजे app
redeploy झाल्यावर local SQLite file रिसेट होऊ शकते. मोठ्या प्रमाणावर
वापरासाठी ही file ऐवजी hosted Postgres (उदा. Supabase) वापरणं योग्य ठरेल.
"""

import sqlite3
from datetime import date

DB_PATH = "app_data.db"

FREE_LIMITS = {
    "pdf_report": 3,        # दिवसाला किती PDF reports
    "sector_screener": 5,   # दिवसाला किती sector-scan runs
}


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            username TEXT PRIMARY KEY,
            tier TEXT NOT NULL DEFAULT 'FREE',
            expiry_date TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_log (
            username TEXT, feature TEXT, usage_date TEXT, count INTEGER DEFAULT 0,
            PRIMARY KEY (username, feature, usage_date)
        )
    """)
    return conn


def get_tier(username: str) -> str:
    conn = _get_conn()
    row = conn.execute(
        "SELECT tier, expiry_date FROM subscriptions WHERE username=?", (username,)
    ).fetchone()
    conn.close()
    if not row:
        return "FREE"
    tier, expiry = row
    if tier == "PRO" and expiry and date.fromisoformat(expiry) < date.today():
        return "FREE"  # subscription expired
    return tier


def get_expiry(username: str):
    conn = _get_conn()
    row = conn.execute("SELECT expiry_date FROM subscriptions WHERE username=?", (username,)).fetchone()
    conn.close()
    return row[0] if row else None


def set_pro(username: str, expiry_date_iso: str):
    conn = _get_conn()
    conn.execute("""
        INSERT INTO subscriptions (username, tier, expiry_date) VALUES (?, 'PRO', ?)
        ON CONFLICT(username) DO UPDATE SET tier='PRO', expiry_date=excluded.expiry_date
    """, (username, expiry_date_iso))
    conn.commit()
    conn.close()


def usage_today(username: str, feature: str) -> int:
    today = date.today().isoformat()
    conn = _get_conn()
    row = conn.execute(
        "SELECT count FROM usage_log WHERE username=? AND feature=? AND usage_date=?",
        (username, feature, today),
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def check_and_increment(username: str, feature: str, limit: int = None) -> bool:
    """
    Free-tier daily usage gate. PRO युजर्ससाठी नेहमी True (मर्यादा नाही).
    Free युजरने आजची मर्यादा ओलांडली असेल तर False (feature वापरू देऊ नये).
    वापरण्यायोग्य असेल तर usage +1 करून True परत देतं.
    """
    if get_tier(username) == "PRO":
        return True

    limit = limit if limit is not None else FREE_LIMITS.get(feature, 10**9)
    today = date.today().isoformat()
    conn = _get_conn()
    row = conn.execute(
        "SELECT count FROM usage_log WHERE username=? AND feature=? AND usage_date=?",
        (username, feature, today),
    ).fetchone()
    current = row[0] if row else 0

    if current >= limit:
        conn.close()
        return False

    conn.execute("""
        INSERT INTO usage_log (username, feature, usage_date, count) VALUES (?, ?, ?, 1)
        ON CONFLICT(username, feature, usage_date) DO UPDATE SET count = count + 1
    """, (username, feature, today))
    conn.commit()
    conn.close()
    return True
