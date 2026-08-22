"""
News + Sentiment Layer.

डेटा स्त्रोत: सार्वजनिक RSS feeds (Economic Times, Moneycontrol, Livemint) —
कुठलंही paid/scraping-आधारित API नाही, त्यामुळे legal दृष्ट्या सुरक्षित.

⚠️ NOTE: खालचे RSS URLs सध्या ज्ञात असलेले आहेत, पण publishers हे URL
कधीही बदलू शकतात. वापरण्याआधी एकदा browser मध्ये उघडून तपासा — हा sandbox
या डोमेन्सपर्यंत पोहोचू शकत नाही त्यामुळे मी स्वतः live verify करू शकलो नाही.

Sentiment: हे साधं keyword/lexicon-based classifier आहे — ML मॉडेल नाही.
हे फक्त एक दिशादर्शक (directional) संकेत आहे, अचूक भावना-विश्लेषण नाही.
"""

import re
from datetime import datetime
from typing import List, Dict

import feedparser

NEWS_SOURCES = {
    "Economic Times Markets": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "Moneycontrol Markets": "https://www.moneycontrol.com/rss/marketreports.xml",
    "Livemint Markets": "https://www.livemint.com/rss/markets",
}

# --- साधा lexicon-based sentiment (शब्द-आधारित, ML नाही) ---
POSITIVE_WORDS = [
    "profit", "growth", "surge", "record", "upgrade", "outperform", "rally",
    "gain", "beat estimates", "strong", "expansion", "bullish", "jump",
    "robust", "healthy", "upbeat", "buyback", "dividend hike", "order win",
    "नफा", "वाढ", "तेजी", "उच्चांक",
]
NEGATIVE_WORDS = [
    "loss", "decline", "downgrade", "plunge", "crash", "miss estimates",
    "fraud", "probe", "resignation", "default", "weak", "bearish", "fall",
    "slump", "layoff", "lawsuit", "penalty", "scam", "investigation",
    "तोटा", "घसरण", "मंदी",
]


def score_sentiment(text: str) -> Dict:
    """साधं keyword-count based classification. -1..+1 range चा score."""
    text_lower = (text or "").lower()
    pos_hits = sum(1 for w in POSITIVE_WORDS if w.lower() in text_lower)
    neg_hits = sum(1 for w in NEGATIVE_WORDS if w.lower() in text_lower)
    total = pos_hits + neg_hits
    if total == 0:
        return {"label": "NEUTRAL", "score": 0.0}
    score = (pos_hits - neg_hits) / total
    if score > 0.15:
        label = "POSITIVE"
    elif score < -0.15:
        label = "NEGATIVE"
    else:
        label = "NEUTRAL"
    return {"label": label, "score": round(score, 2)}


def _fetch_source(name: str, url: str, timeout: int = 8) -> List[Dict]:
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            print(f"[NEWS] '{name}' feed parse issue: {feed.bozo_exception}")
            return []
        items = []
        for entry in feed.entries:
            items.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", entry.get("description", "")),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": name,
            })
        return items
    except Exception as e:
        print(f"[NEWS] '{name}' fetch failed: {e}")
        return []


def fetch_all_news() -> List[Dict]:
    all_items = []
    for name, url in NEWS_SOURCES.items():
        all_items.extend(_fetch_source(name, url))
    return all_items


def _dedup_by_title(items: List[Dict]) -> List[Dict]:
    seen_titles = set()
    deduped = []
    for item in items:
        key = item["title"].strip().lower()
        if key and key not in seen_titles:
            seen_titles.add(key)
            deduped.append(item)
    return deduped


def get_news_for_ticker(ticker: str, company_name: str = "", max_items: int = 10) -> List[Dict]:
    """
    दिलेल्या ticker/company शी संबंधित बातम्या फिल्टर करून, प्रत्येकीला
    sentiment label लावून परत देतो. कुठलीही बातमी सापडली नाही तर रिकामी
    यादी (fake बातम्या कधीच बनवत नाही).
    """
    all_news = fetch_all_news()
    clean_symbol = ticker.replace(".NS", "").replace(".BO", "")
    search_terms = [t for t in [clean_symbol, company_name] if t]

    if not search_terms:
        return []

    pattern = re.compile("|".join(re.escape(t) for t in search_terms), re.IGNORECASE)

    relevant = []
    for item in all_news:
        haystack = f"{item['title']} {item['summary']}"
        if pattern.search(haystack):
            sentiment = score_sentiment(haystack)
            relevant.append({**item, **sentiment})

    return _dedup_by_title(relevant)[:max_items]


def get_sector_news(sector_keywords: List[str], max_items: int = 15) -> List[Dict]:
    """Sector-level बातम्या — sector च्या keyword(s) शी title/summary मॅच होणाऱ्या."""
    all_news = fetch_all_news()
    if not sector_keywords:
        return []
    pattern = re.compile("|".join(re.escape(k) for k in sector_keywords), re.IGNORECASE)
    relevant = []
    for item in all_news:
        haystack = f"{item['title']} {item['summary']}"
        if pattern.search(haystack):
            sentiment = score_sentiment(haystack)
            relevant.append({**item, **sentiment})
    return _dedup_by_title(relevant)[:max_items]
