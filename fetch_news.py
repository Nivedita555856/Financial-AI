"""
Daily News Fetcher - Financial Insights Copilot
Uses GDELT API (free, no key required)
Run manually: python fetch_news.py
Auto-runs from api.py on startup if news is older than 24 hours
"""

import json
import requests
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
NEWS_DIR = BASE_DIR / "financial_data" / "news_data"
NEWS_DIR.mkdir(parents=True, exist_ok=True)

COMPANIES = {
    "AAPL":  "Apple AAPL stock",
    "MSFT":  "Microsoft MSFT stock",
    "GOOGL": "Google Alphabet GOOGL stock",
    "AMZN":  "Amazon AMZN stock",
    "TSLA":  "Tesla TSLA stock",
    "NVDA":  "NVIDIA NVDA stock",
}

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def fetch_gdelt_news(ticker: str, query: str, limit: int = 15) -> list:
    """Fetch news from GDELT API — free, no key required."""
    try:
        params = {
            "query":      query,
            "mode":       "artlist",
            "maxrecords": limit,
            "format":     "json",
            "timespan":   "7d",
            "sort":       "DateDesc",
        }
        r = requests.get(GDELT_URL, params=params, timeout=15)
        if r.status_code != 200:
            logger.warning(f"GDELT returned {r.status_code} for {ticker}")
            return []

        articles = r.json().get("articles", [])
        cleaned = []
        for a in articles:
            cleaned.append({
                "source":       "GDELT",
                "title":        a.get("title", ""),
                "description":  a.get("seendate", ""),
                "url":          a.get("url", ""),
                "published_at": a.get("seendate", ""),
                "source_country": a.get("sourcecountry", ""),
                "is_sample":    False,
            })
        logger.info(f"  {ticker}: {len(cleaned)} articles fetched")
        return cleaned

    except Exception as e:
        logger.error(f"GDELT fetch failed for {ticker}: {e}")
        return []


def news_needs_refresh(ticker: str, max_age_hours: int = 24) -> bool:
    """Check if news file is older than max_age_hours."""
    path = NEWS_DIR / f"{ticker}_news.json"
    if not path.exists():
        return True
    try:
        data = json.loads(path.read_text())
        # check if sample data
        arts = data.get("articles", [])
        if arts and arts[0].get("is_sample"):
            return True
        # check age
        collected = data.get("collection_date", "")
        if not collected:
            return True
        collected_dt = datetime.fromisoformat(collected.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - collected_dt).total_seconds() / 3600
        return age_hours > max_age_hours
    except Exception:
        return True


def save_news(ticker: str, articles: list):
    """Save articles to JSON file."""
    path = NEWS_DIR / f"{ticker}_news.json"
    data = {
        "ticker":          ticker,
        "collection_date": datetime.now(timezone.utc).isoformat(),
        "articles":        articles,
    }
    path.write_text(json.dumps(data, indent=2))
    logger.info(f"  Saved {len(articles)} articles → {path.name}")


def refresh_all_news(force: bool = False) -> dict:
    """
    Refresh news for all companies.
    Skips tickers where news is fresh (< 24h) unless force=True.
    Returns summary dict.
    """
    summary = {}
    logger.info("Starting news refresh...")

    for ticker, query in COMPANIES.items():
        if not force and not news_needs_refresh(ticker):
            logger.info(f"  {ticker}: skipped (news is fresh)")
            summary[ticker] = "skipped"
            continue

        articles = fetch_gdelt_news(ticker, query, limit=15)
        if articles:
            save_news(ticker, articles)
            summary[ticker] = len(articles)
        else:
            logger.warning(f"  {ticker}: no articles, keeping existing data")
            summary[ticker] = "no new articles"

    logger.info(f"News refresh complete: {summary}")
    return summary


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    summary = refresh_all_news(force=force)
    print("\nSummary:")
    for ticker, result in summary.items():
        print(f"  {ticker}: {result}")
