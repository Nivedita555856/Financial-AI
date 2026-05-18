"""
FastAPI Backend for Financial Insights Copilot - Graph RAG
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import uvicorn
import logging

# Import your GraphRAG class
from graph_rag import GraphRAG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Financial Insights Copilot API", version="1.0.0")

# CORS - Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize GraphRAG globally
rag = None


class QuestionRequest(BaseModel):
    question: str
    ticker: Optional[str] = None


class ImpactRequest(BaseModel):
    ticker: str
    issue: str


@app.on_event("startup")
async def startup_event():
    """Connect to databases on startup"""
    global rag
    rag = GraphRAG()
    success = rag.connect()
    if success:
        logger.info("✅ GraphRAG initialized and connected to databases")
    else:
        logger.warning("⚠️ GraphRAG initialized but database connection failed")


@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown"""
    global rag
    if rag:
        rag.close()
        logger.info("🔒 Connections closed")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Financial Insights Copilot"}


@app.post("/api/ask")
async def ask_question(request: QuestionRequest):
    """Ask a financial question"""
    global rag
    try:
        if not rag:
            raise HTTPException(status_code=500, detail="GraphRAG not initialized")
        
        if request.ticker:
            answer = rag.ask_general(request.question, request.ticker)
        else:
            answer = rag.ask_general(request.question)
        
        return {
            "answer": answer,
            "question": request.question,
            "ticker": request.ticker,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error in ask_question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/impact")
async def analyze_impact(request: ImpactRequest):
    """Analyze impact of an issue on a company"""
    global rag
    try:
        if not rag:
            raise HTTPException(status_code=500, detail="GraphRAG not initialized")
        
        answer = rag.ask_impact(request.ticker, request.issue)
        
        return {
            "ticker": request.ticker,
            "issue": request.issue,
            "analysis": answer,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error in analyze_impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/financials/{ticker}")
async def get_financials(ticker: str):
    """Get financial data for a company"""
    global rag
    try:
        if not rag:
            raise HTTPException(status_code=500, detail="GraphRAG not initialized")
        
        data = rag.get_company_financials(ticker)
        return {
            "ticker": ticker,
            "financials": data.get('financials', []),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error in get_financials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/companies")
async def get_companies():
    """Get list of available companies"""
    global rag
    try:
        if not rag:
            raise HTTPException(status_code=500, detail="GraphRAG not initialized")
        
        companies = rag.get_all_companies()
        return {"companies": companies, "status": "success"}
    except Exception as e:
        logger.error(f"Error in get_companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/{ticker}")
async def get_news(ticker: str, limit: int = 5):
    """Get news for a company"""
    global rag
    try:
        if not rag:
            raise HTTPException(status_code=500, detail="GraphRAG not initialized")
        
        news = rag.search_weaviate(f"{ticker} news", ticker, limit)
        return {
            "ticker": ticker,
            "news": news,
            "count": len(news),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error in get_news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )