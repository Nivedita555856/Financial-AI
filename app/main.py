"""
FastAPI Backend - Financial Insights Copilot
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn, logging, asyncio

from app.graph_rag import GraphRAG
from app.fetch_news import refresh_all_news, news_needs_refresh
from app.market_data import fetch_all_prices, get_market_summary, analyze_sentiment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Financial Insights Copilot API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

rag = None

class QuestionRequest(BaseModel):
    question: str
    ticker: Optional[str] = None

class ImpactRequest(BaseModel):
    ticker: str
    issue: str


@app.on_event("startup")
async def startup_event():
    global rag
    rag = GraphRAG()
    rag.connect()
    logger.info("GraphRAG initialized")
    asyncio.create_task(_background_startup())


async def _background_startup():
    await asyncio.sleep(3)
    try:
        stale = [t for t in ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA"] if news_needs_refresh(t)]
        if stale:
            logger.info(f"Refreshing news for: {stale}")
            refresh_all_news()
            rag._load_news()
            logger.info("News refreshed")
    except Exception as e:
        logger.warning(f"Background startup failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    if rag: rag.close()


# ── Health ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status":   "healthy",
        "service":  "Financial Insights Copilot",
        "neo4j":    "connected" if (rag and rag.use_neo4j)    else "local",
        "weaviate": "connected" if (rag and rag.use_weaviate) else "local",
    }


# ── Core RAG endpoints ────────────────────────────────────────────────────

@app.post("/api/ask")
async def ask_question(request: QuestionRequest):
    try:
        if not rag: raise HTTPException(500, "GraphRAG not initialized")
        answer = rag.ask_general(request.question, request.ticker)
        return {"answer": answer, "question": request.question,
                "ticker": request.ticker, "status": "success"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/impact")
async def analyze_impact(request: ImpactRequest):
    try:
        if not rag: raise HTTPException(500, "GraphRAG not initialized")
        return {"ticker": request.ticker, "issue": request.issue,
                "analysis": rag.ask_impact(request.ticker, request.issue),
                "status": "success"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/financials/{ticker}")
async def get_financials(ticker: str):
    try:
        if not rag: raise HTTPException(500, "GraphRAG not initialized")
        data = rag.get_company_financials(ticker)
        return {"ticker": ticker, "financials": data.get("financials", []), "status": "success"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/companies")
async def get_companies():
    try:
        if not rag: raise HTTPException(500, "GraphRAG not initialized")
        return {"companies": rag.get_all_companies(), "status": "success"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/news/{ticker}")
async def get_news(ticker: str, limit: int = 10):
    news = []
    try:
        if rag:
            news = rag.search_weaviate(f"{ticker} news", ticker, limit)
    except Exception as e:
        logger.error(f"search_weaviate error {ticker}: {e}")
    try:
        sentiment = analyze_sentiment(news)
    except Exception:
        sentiment = {"score": 0.0, "label": "Neutral", "count": 0}
    return {"ticker": ticker, "news": news, "count": len(news),
            "sentiment": sentiment, "status": "success"}

@app.get("/api/prices")
async def get_prices():
    """Live stock prices for all 6 companies (cached 15 min)."""
    try:
        prices = fetch_all_prices()
        return {"prices": prices, "status": "success"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/prices/{ticker}")
async def get_price(ticker: str):
    """Live stock price for a single ticker."""
    try:
        prices = fetch_all_prices()
        data = prices.get(ticker.upper())
        if not data: raise HTTPException(404, f"Ticker {ticker} not found")
        return {"ticker": ticker.upper(), **data, "status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/sentiment/{ticker}")
async def get_sentiment(ticker: str):
    """News sentiment score for a ticker."""
    try:
        if not rag: raise HTTPException(500, "GraphRAG not initialized")
        news = rag.search_weaviate(f"{ticker} news", ticker, 15)
        sentiment = analyze_sentiment(news)
        return {"ticker": ticker.upper(), "sentiment": sentiment, "status": "success"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/summary/{ticker}")
async def get_summary(ticker: str):
    """Full market summary: price + sentiment + latest news headline."""
    try:
        if not rag: raise HTTPException(500, "GraphRAG not initialized")
        news = rag.search_weaviate(f"{ticker} news", ticker, 15)
        summary = get_market_summary(ticker, news)
        return {**summary, "status": "success"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/market-overview")
async def get_market_overview():
    """Overview of all 6 companies: price + sentiment in one call."""
    try:
        if not rag: raise HTTPException(500, "GraphRAG not initialized")
        prices = fetch_all_prices()
        overview = []
        for ticker in ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA"]:
            news = rag.search_weaviate(f"{ticker} news", ticker, 10)
            sentiment = analyze_sentiment(news)
            overview.append({
                "ticker":    ticker,
                "name":      prices.get(ticker, {}).get("name", ticker),
                "price":     prices.get(ticker, {}).get("price"),
                "change":    prices.get(ticker, {}).get("change"),
                "change_pct":prices.get(ticker, {}).get("change_pct"),
                "sentiment": sentiment,
            })
        return {"overview": overview, "status": "success"}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/relationships/{ticker}")
async def get_relationships(ticker: str):
    """Graph relationships for a ticker."""
    try:
        if not rag: raise HTTPException(500, "GraphRAG not initialized")
        return {
            "ticker":      ticker.upper(),
            "suppliers":   rag.get_suppliers(ticker),
            "customers":   rag.get_customers(ticker),
            "competitors": rag.get_competitors(ticker),
            "partners":    rag.get_partners(ticker),
            "status":      "success",
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ── News refresh ──────────────────────────────────────────────────────────

@app.post("/api/news/refresh")
async def refresh_news(background_tasks: BackgroundTasks, force: bool = False):
    def _run():
        refresh_all_news(force=force)
        if rag: rag._load_news()
    background_tasks.add_task(_run)
    return {"status": "refresh started"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
