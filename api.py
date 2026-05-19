"""
FastAPI Backend for Financial Insights Copilot - Graph RAG
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import logging

from graph_rag import GraphRAG
from fetch_news import refresh_all_news, news_needs_refresh

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Financial Insights Copilot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    logger.info("✅ GraphRAG initialized")

    # Refresh news in background if stale
    import asyncio
    asyncio.create_task(_refresh_news_background())


async def _refresh_news_background():
    """Refresh news for any ticker that has stale/sample data."""
    import asyncio
    await asyncio.sleep(3)  # let startup finish first
    try:
        tickers_needed = [t for t in ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA"]
                          if news_needs_refresh(t)]
        if tickers_needed:
            logger.info(f"Auto-refreshing news for: {tickers_needed}")
            refresh_all_news()
            # Reload news into rag
            rag._load_news()
            logger.info("✅ News refreshed and reloaded")
    except Exception as e:
        logger.warning(f"Background news refresh failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    global rag
    if rag:
        rag.close()


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Financial Insights Copilot",
        "neo4j": "connected" if (rag and rag.use_neo4j) else "local",
        "weaviate": "connected" if (rag and rag.use_weaviate) else "local",
    }


@app.post("/api/ask")
async def ask_question(request: QuestionRequest):
    global rag
    try:
        if not rag:
            raise HTTPException(status_code=500, detail="GraphRAG not initialized")
        answer = rag.ask_general(request.question, request.ticker)
        return {"answer": answer, "question": request.question,
                "ticker": request.ticker, "status": "success"}
    except Exception as e:
        logger.error(f"Error in ask_question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/impact")
async def analyze_impact(request: ImpactRequest):
    global rag
    try:
        if not rag:
            raise HTTPException(status_code=500, detail="GraphRAG not initialized")
        answer = rag.ask_impact(request.ticker, request.issue)
        return {"ticker": request.ticker, "issue": request.issue,
                "analysis": answer, "status": "success"}
    except Exception as e:
        logger.error(f"Error in analyze_impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/financials/{ticker}")
async def get_financials(ticker: str):
    global rag
    try:
        if not rag:
            raise HTTPException(status_code=500, detail="GraphRAG not initialized")
        data = rag.get_company_financials(ticker)
        return {"ticker": ticker, "financials": data.get("financials", []),
                "status": "success"}
    except Exception as e:
        logger.error(f"Error in get_financials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/companies")
async def get_companies():
    global rag
    try:
        if not rag:
            raise HTTPException(status_code=500, detail="GraphRAG not initialized")
        return {"companies": rag.get_all_companies(), "status": "success"}
    except Exception as e:
        logger.error(f"Error in get_companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/{ticker}")
async def get_news(ticker: str, limit: int = 10):
    global rag
    try:
        if not rag:
            raise HTTPException(status_code=500, detail="GraphRAG not initialized")
        news = rag.search_weaviate(f"{ticker} news", ticker, limit)
        return {"ticker": ticker, "news": news, "count": len(news), "status": "success"}
    except Exception as e:
        logger.error(f"Error in get_news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/news/refresh")
async def refresh_news(background_tasks: BackgroundTasks, force: bool = False):
    """Manually trigger a news refresh for all companies."""
    def _run():
        global rag
        summary = refresh_all_news(force=force)
        if rag:
            rag._load_news()
        return summary
    background_tasks.add_task(_run)
    return {"status": "refresh started", "message": "News will be updated in background"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True, log_level="info")
