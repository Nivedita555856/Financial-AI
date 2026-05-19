"""
News Fetcher - Financial Insights Copilot
Primary:  yfinance (already installed, Yahoo Finance news)
Fallback: Yahoo Finance RSS
Fallback: GDELT
"""

import json, logging, requests
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
NEWS_DIR = BASE_DIR / "financial_data" / "news_data"
NEWS_DIR.mkdir(parents=True, exist_ok=True)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]


# ── Source 1: yfinance ────────────────────────────────────────────────────

def fetch_yfinance_news(ticker: str, limit: int = 15) -> list:
    try:
        import yfinance as yf
        from datetime import datetime, timezone
        t = yf.Ticker(ticker)
        raw = t.news or []
        articles = []
        for a in raw[:limit]:
            ts = a.get("providerPublishTime", 0)
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else ""
            title = a.get("title", "")
            if not title:
                continue
            articles.append({
                "source":       a.get("publisher", "Yahoo Finance"),
                "title":        title,
                "url":          a.get("link", ""),
                "published_at": dt,
                "is_sample":    False,
            })
        logger.info(f"  yfinance {ticker}: {len(articles)} articles")
        return articles
    except Exception as e:
        logger.warning(f"  yfinance failed for {ticker}: {e}")
        return []


# ── Source 2: Yahoo Finance RSS ───────────────────────────────────────────

def fetch_rss_news(ticker: str, limit: int = 15) -> list:
    try:
        import xml.etree.ElementTree as ET
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.text)
        articles = []
        for item in root.findall(".//item")[:limit]:
            title = (item.findtext("title") or "").strip()
            if not title:
                continue
            articles.append({
                "source":       "Yahoo Finance",
                "title":        title,
                "url":          item.findtext("link") or "",
                "published_at": item.findtext("pubDate") or "",
                "is_sample":    False,
            })
        logger.info(f"  RSS {ticker}: {len(articles)} articles")
        return articles
    except Exception as e:
        logger.warning(f"  RSS failed for {ticker}: {e}")
        return []


# ── Source 3: GDELT ───────────────────────────────────────────────────────

def fetch_gdelt_news(ticker: str, query: str, limit: int = 15) -> list:
    QUERIES = {
        "AAPL": "Apple AAPL stock", "MSFT": "Microsoft MSFT stock",
        "GOOGL": "Google Alphabet GOOGL", "AMZN": "Amazon AMZN stock",
        "TSLA": "Tesla TSLA stock", "NVDA": "NVIDIA NVDA stock",
    }
    try:
        r = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": QUERIES.get(ticker, f"{ticker} stock"), "mode": "artlist",
                    "maxrecords": limit, "format": "json", "timespan": "7d", "sort": "DateDesc"},
            timeout=15
        )
        if r.status_code != 200:
            return []
        arts = r.json().get("articles", [])
        return [{"source": "GDELT", "title": a.get("title", ""),
                 "url": a.get("url", ""), "published_at": a.get("seendate", ""),
                 "is_sample": False} for a in arts if a.get("title")]
    except Exception as e:
        logger.warning(f"  GDELT failed for {ticker}: {e}")
        return []


# ── Main fetch logic ──────────────────────────────────────────────────────

def fetch_news_for_ticker(ticker: str, limit: int = 15) -> list:
    """Try all sources in order, return first that works."""
    for fn in [fetch_yfinance_news, fetch_rss_news,
               lambda t, l: fetch_gdelt_news(t, t, l)]:
        try:
            arts = fn(ticker, limit)
            if arts:
                return arts
        except Exception:
            continue
    return []


def news_needs_refresh(ticker: str, max_age_hours: int = 24) -> bool:
    path = NEWS_DIR / f"{ticker}_news.json"
    if not path.exists():
        return True
    try:
        raw = path.read_bytes().replace(b"\x00", b"")
        data = json.loads(raw.decode("utf-8", errors="ignore"))
        arts = data.get("articles", [])
        if not arts or arts[0].get("is_sample"):
            return True
        collected = data.get("collection_date", "")
        if not collected:
            return True
        dt = datetime.fromisoformat(collected.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return age > max_age_hours
    except Exception:
        return True


def save_news(ticker: str, articles: list):
    path = NEWS_DIR / f"{ticker}_news.json"
    path.write_text(json.dumps({
        "ticker":          ticker,
        "collection_date": datetime.now(timezone.utc).isoformat(),
        "articles":        articles,
    }, indent=2, ensure_ascii=False), encoding="utf-8")


def refresh_all_news(force: bool = False) -> dict:
    summary = {}
    for ticker in TICKERS:
        if not force and not news_needs_refresh(ticker):
            summary[ticker] = "fresh"
            logger.info(f"  {ticker}: skipped (fresh)")
            continue
        logger.info(f"Fetching news for {ticker}...")
        articles = fetch_news_for_ticker(ticker)
        if articles:
            save_news(ticker, articles)
            summary[ticker] = len(articles)
            logger.info(f"  {ticker}: saved {len(articles)} articles")
        else:
            summary[ticker] = "no articles"
            logger.warning(f"  {ticker}: no articles from any source")
    return summary


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    force = "--force" in sys.argv
    print(f"Fetching news (force={force})...\n")
    result = refresh_all_news(force=force)
    print("\nResults:")
    for ticker, val in result.items():
        print(f"  {ticker}: {val}")
