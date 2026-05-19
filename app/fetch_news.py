"""
Daily News Fetcher - uses GDELT API (free, no key required)
"""

import json, requests, logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
NEWS_DIR = BASE_DIR / "data" / "financial" / "news_data"
NEWS_DIR.mkdir(parents=True, exist_ok=True)

COMPANIES = {
    "AAPL":  "Apple AAPL stock",
    "MSFT":  "Microsoft MSFT stock",
    "GOOGL": "Google Alphabet GOOGL stock",
    "AMZN":  "Amazon AMZN stock",
    "TSLA":  "Tesla TSLA stock",
    "NVDA":  "NVIDIA NVDA stock",
}


def fetch_gdelt_news(ticker: str, query: str, limit: int = 15) -> list:
    try:
        r = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": query, "mode": "artlist", "maxrecords": limit,
                    "format": "json", "timespan": "7d", "sort": "DateDesc"},
            timeout=15
        )
        if r.status_code != 200:
            return []
        articles = r.json().get("articles", [])
        return [{"source": "GDELT", "title": a.get("title",""),
                 "url": a.get("url",""), "published_at": a.get("seendate",""),
                 "source_country": a.get("sourcecountry",""), "is_sample": False}
                for a in articles]
    except Exception as e:
        logger.error(f"GDELT fetch failed for {ticker}: {e}")
        return []


def news_needs_refresh(ticker: str, max_age_hours: int = 24) -> bool:
    path = NEWS_DIR / f"{ticker}_news.json"
    if not path.exists(): return True
    try:
        data = json.loads(path.read_text())
        arts = data.get("articles", [])
        if arts and arts[0].get("is_sample"): return True
        collected = data.get("collection_date", "")
        if not collected: return True
        dt = datetime.fromisoformat(collected.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600 > max_age_hours
    except Exception:
        return True


def save_news(ticker: str, articles: list):
    path = NEWS_DIR / f"{ticker}_news.json"
    path.write_text(json.dumps({
        "ticker": ticker,
        "collection_date": datetime.now(timezone.utc).isoformat(),
        "articles": articles,
    }, indent=2))
    logger.info(f"Saved {len(articles)} articles for {ticker}")


def refresh_all_news(force: bool = False) -> dict:
    summary = {}
    for ticker, query in COMPANIES.items():
        if not force and not news_needs_refresh(ticker):
            summary[ticker] = "skipped"
            continue
        articles = fetch_gdelt_news(ticker, query, limit=15)
        if articles:
            save_news(ticker, articles)
            summary[ticker] = len(articles)
        else:
            summary[ticker] = "no new articles"
    logger.info(f"News refresh: {summary}")
    return summary


if __name__ == "__main__":
    import sys
    result = refresh_all_news(force="--force" in sys.argv)
    for ticker, val in result.items():
        print(f"  {ticker}: {val}")
