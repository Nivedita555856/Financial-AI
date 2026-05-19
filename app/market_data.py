"""
Market Data & Sentiment - Financial Insights Copilot
Live stock prices via yfinance + VADER sentiment on news
"""

import json, logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).parent.parent
CACHE_FILE = BASE_DIR / "data" / "financial" / "prices_cache.json"
CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]

COMPANY_NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet",
    "AMZN": "Amazon", "TSLA": "Tesla",    "NVDA":  "NVIDIA",
}


# ── Sentiment ──────────────────────────────────────────────────────────────

def analyze_sentiment(articles: List[Dict]) -> Dict:
    """Run VADER sentiment on news titles. Returns score + label."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
        scores = []
        for a in articles:
            title = a.get("title", "")
            if title and title != "placeholder":
                scores.append(sia.polarity_scores(title)["compound"])
        if not scores:
            return {"score": 0.0, "label": "Neutral", "count": 0}
        avg = sum(scores) / len(scores)
        label = "Positive" if avg >= 0.05 else "Negative" if avg <= -0.05 else "Neutral"
        return {"score": round(avg, 3), "label": label, "count": len(scores)}
    except ImportError:
        return {"score": 0.0, "label": "Neutral", "count": 0}
    except Exception as e:
        logger.warning(f"Sentiment error: {e}")
        return {"score": 0.0, "label": "Neutral", "count": 0}


# ── Price fetching ──────────────────────────────────────────────────────────

def _load_cache() -> Dict:
    try:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_cache(data: Dict):
    try:
        CACHE_FILE.write_text(json.dumps(data, indent=2))
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")


def _cache_is_fresh(cache: Dict, max_age_minutes: int = 15) -> bool:
    ts = cache.get("_timestamp")
    if not ts:
        return False
    try:
        dt = datetime.fromisoformat(ts)
        return (datetime.now(timezone.utc) - dt).total_seconds() < max_age_minutes * 60
    except Exception:
        return False


def fetch_all_prices() -> Dict:
    """
    Fetch live prices for all tickers via yfinance.
    Cached for 15 minutes to avoid rate limits.
    Returns {AAPL: {price, change, change_pct, volume, market_cap}, ...}
    """
    cache = _load_cache()
    if _cache_is_fresh(cache):
        logger.info("Prices from cache")
        return {k: v for k, v in cache.items() if not k.startswith("_")}

    try:
        import yfinance as yf
        data = {}
        tickers_obj = yf.Tickers(" ".join(TICKERS))
        for ticker in TICKERS:
            try:
                info = tickers_obj.tickers[ticker].fast_info
                price      = round(float(info.last_price or 0), 2)
                prev_close = round(float(info.previous_close or price), 2)
                change     = round(price - prev_close, 2)
                change_pct = round((change / prev_close * 100) if prev_close else 0, 2)
                data[ticker] = {
                    "price":      price,
                    "change":     change,
                    "change_pct": change_pct,
                    "prev_close": prev_close,
                    "name":       COMPANY_NAMES.get(ticker, ticker),
                    "currency":   "USD",
                }
            except Exception as e:
                logger.warning(f"Price fetch failed for {ticker}: {e}")
                data[ticker] = _empty_price(ticker)

        cache = {"_timestamp": datetime.now(timezone.utc).isoformat(), **data}
        _save_cache(cache)
        logger.info(f"Prices fetched for {list(data.keys())}")
        return data

    except ImportError:
        logger.warning("yfinance not installed — returning empty prices")
        return {t: _empty_price(t) for t in TICKERS}
    except Exception as e:
        logger.error(f"Price fetch error: {e}")
        return {t: _empty_price(t) for t in TICKERS}


def _empty_price(ticker: str) -> Dict:
    return {"price": None, "change": None, "change_pct": None,
            "prev_close": None, "name": COMPANY_NAMES.get(ticker, ticker), "currency": "USD"}


def get_market_summary(ticker: str, news: List[Dict]) -> Dict:
    """Full summary: price + sentiment + latest headline."""
    prices = fetch_all_prices()
    price_data = prices.get(ticker.upper(), _empty_price(ticker))
    sentiment  = analyze_sentiment(news)
    latest     = next((a.get("title") for a in news if a.get("title") and a.get("title") != "placeholder"), None)
    return {
        "ticker":     ticker.upper(),
        "name":       COMPANY_NAMES.get(ticker.upper(), ticker),
        "price":      price_data,
        "sentiment":  sentiment,
        "latest_news": latest,
    }
