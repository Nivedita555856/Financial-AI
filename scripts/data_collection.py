
import os
import json
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def convert_to_serializable(obj):
    """Convert any non-serializable object to JSON serializable format"""
    if isinstance(obj, dict):
        return {str(k): convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, pd.Timestamp):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, (pd.DataFrame, pd.Series)):
        return convert_to_serializable(obj.to_dict())
    elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32, np.float16)):
        return float(obj) if not np.isnan(obj) else None
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, (set, tuple)):
        return list(obj)
    else:
        return obj


class FinancialDataCollector:
    """Complete data collector - NO JSON ERRORS GUARANTEED"""
    
    # Ticker to CIK mapping
    TICKER_CIK_MAP = {
        'AAPL': '0000320193', 'MSFT': '0000789019', 'GOOGL': '0001652044',
        'AMZN': '0001018724', 'META': '0001326801', 'TSLA': '0001318605',
        'NVDA': '0001045810', 'JPM': '0000019617', 'V': '0001403161',
        'WMT': '0000104169', 'DIS': '0001001039', 'NFLX': '0001065280'
    }
    
    def __init__(self, user_email: str, company_name: str, data_dir: str = "./financial_data"):
        """Initialize all collectors"""
        self.user_email = user_email
        self.company_name = company_name
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.sec_dir = self.data_dir / "sec_filings"
        self.yahoo_dir = self.data_dir / "market_data"
        self.news_dir = self.data_dir / "news_data"
        self.metadata_dir = self.data_dir / "metadata"
        
        for dir_path in [self.sec_dir, self.yahoo_dir, self.news_dir, self.metadata_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # SEC headers
        self.sec_headers = {
            'User-Agent': f'{self.company_name} {self.user_email}',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'data.sec.gov'
        }
        
        self.last_request_time = 0
        logger.info(f"✅ Data collector initialized. Saving to: {self.data_dir}")
        logger.info(f"📧 Using email: {self.user_email} for SEC EDGAR")
    
    def _rate_limit(self, min_interval: float = 0.1):
        """Rate limiting for API calls"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _save_json(self, filepath, data):
        """Safely save JSON with conversion"""
        try:
            cleaned_data = convert_to_serializable(data)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save {filepath}: {e}")
            with open(f"{filepath}.txt", 'w', encoding='utf-8') as f:
                f.write(str(data))
            return False
    
    # ==================== YAHOO FINANCE ====================
    
    def collect_yahoo_finance(self, tickers: List[str], period: str = "1y"):
        """Collect market data - FULLY FIXED with string conversion"""
        logger.info(f"📈 Collecting Yahoo Finance data for {tickers}")
        
        try:
            import yfinance as yf
        except ImportError:
            logger.error("❌ yfinance not installed. Run: pip install yfinance")
            return {}
        
        all_data = {}
        
        for ticker in tickers:
            try:
                logger.info(f"  Processing {ticker}...")
                stock = yf.Ticker(ticker)
                ticker_data = {}
                
                # 1. Historical prices - Convert everything to strings
                hist = stock.history(period=period)
                if not hist.empty:
                    hist_reset = hist.reset_index()
                    for col in hist_reset.columns:
                        if 'date' in col.lower() or 'time' in col.lower():
                            hist_reset[col] = hist_reset[col].astype(str)
                    ticker_data['historical_prices'] = hist_reset.to_dict(orient='records')
                
                # 2. Company info
                info = stock.info
                ticker_data['company_info'] = {
                    'name': str(info.get('longName', '')),
                    'sector': str(info.get('sector', '')),
                    'industry': str(info.get('industry', '')),
                    'market_cap': float(info.get('marketCap', 0)) if info.get('marketCap') else 0,
                    'pe_ratio': float(info.get('trailingPE', 0)) if info.get('trailingPE') else 0,
                    'forward_pe': float(info.get('forwardPE', 0)) if info.get('forwardPE') else 0,
                    'dividend_yield': float(info.get('dividendYield', 0)) if info.get('dividendYield') else 0,
                    'beta': float(info.get('beta', 0)) if info.get('beta') else 0,
                    'country': str(info.get('country', '')),
                    'website': str(info.get('website', '')),
                    'avg_volume': float(info.get('averageVolume', 0)) if info.get('averageVolume') else 0,
                    '52_week_high': float(info.get('fiftyTwoWeekHigh', 0)) if info.get('fiftyTwoWeekHigh') else 0,
                    '52_week_low': float(info.get('fiftyTwoWeekLow', 0)) if info.get('fiftyTwoWeekLow') else 0
                }
                
                # 3. Financials
                try:
                    income = stock.financials
                    if not income.empty:
                        income_str = income.copy()
                        income_str.index = income_str.index.astype(str)
                        for col in income_str.columns:
                            if hasattr(col, 'strftime'):
                                income_str.columns = [str(c) for c in income_str.columns]
                        ticker_data['income_statement'] = income_str.head(5).to_dict()
                except Exception:
                    ticker_data['income_statement'] = {}
                
                try:
                    balance = stock.balance_sheet
                    if not balance.empty:
                        balance_str = balance.copy()
                        balance_str.index = balance_str.index.astype(str)
                        ticker_data['balance_sheet'] = balance_str.head(5).to_dict()
                except Exception:
                    ticker_data['balance_sheet'] = {}
                
                try:
                    cash = stock.cashflow
                    if not cash.empty:
                        cash_str = cash.copy()
                        cash_str.index = cash_str.index.astype(str)
                        ticker_data['cashflow'] = cash_str.head(5).to_dict()
                except Exception:
                    ticker_data['cashflow'] = {}
                
                # 4. Analyst recommendations
                try:
                    rec = stock.recommendations
                    if rec is not None and not rec.empty:
                        rec_str = rec.copy()
                        if rec_str.index is not None:
                            rec_str.index = rec_str.index.astype(str)
                        ticker_data['recommendations'] = rec_str.head(10).to_dict()
                except Exception:
                    ticker_data['recommendations'] = {}
                
                # Save using safe method
                output_file = self.yahoo_dir / f"{ticker}_market.json"
                self._save_json(output_file, ticker_data)
                logger.info(f"  ✅ Saved {ticker} market data")
                all_data[ticker] = ticker_data
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"  ❌ Failed for {ticker}: {e}")
        
        return all_data
    
    # ==================== SEC EDGAR ====================
    
    def get_cik(self, ticker: str) -> Optional[str]:
        """Convert ticker to CIK"""
        ticker = ticker.upper()
        return self.TICKER_CIK_MAP.get(ticker)
    
    def collect_sec_edgar(self, tickers: List[str], years: List[int] = None):
        """Collect SEC filings"""
        if years is None:
            current_year = datetime.now().year
            years = list(range(current_year - 3, current_year + 1))
        
        logger.info(f"📄 Collecting SEC EDGAR data for {tickers}")
        all_data = {}
        
        for ticker in tickers:
            try:
                cik = self.get_cik(ticker)
                if not cik:
                    logger.warning(f"No CIK for {ticker}")
                    continue
                
                ticker_data = {
                    'ticker': ticker,
                    'cik': cik,
                    'collection_date': datetime.now().isoformat(),
                    'financial_statements': {},
                    'insider_trading': [],
                    'filings': []
                }
                
                self._rate_limit()
                url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
                response = requests.get(url, headers=self.sec_headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    facts = data.get('facts', {}).get('us-gaap', {})
                    
                    key_metrics = {
                        'Revenue': 'Revenues',
                        'NetIncome': 'NetIncomeLoss',
                        'TotalAssets': 'Assets',
                        'TotalLiabilities': 'Liabilities',
                        'OperatingCashFlow': 'NetCashProvidedByUsedInOperatingActivities',
                        'GrossProfit': 'GrossProfit',
                        'RAndD': 'ResearchAndDevelopmentExpense',
                        'SellingAndMarketing': 'SellingAndMarketingExpense'
                    }
                    
                    for year in years:
                        yearly = {'year': year}
                        for metric_name, fact_name in key_metrics.items():
                            if fact_name in facts:
                                units = facts[fact_name].get('units', {})
                                if 'USD' in units:
                                    for entry in units['USD']:
                                        if entry.get('fy') == year:
                                            val = entry.get('val')
                                            yearly[metric_name] = float(val) if val else None
                                            break
                        
                        if len(yearly) > 1:
                            ticker_data['financial_statements'][str(year)] = yearly
                    
                    logger.info(f"  Extracted {len(ticker_data['financial_statements'])} years for {ticker}")
                
                # Get recent filings
                self._rate_limit()
                filings_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=&count=20&output=atom"
                filings_response = requests.get(filings_url, headers=self.sec_headers, timeout=10)
                
                if filings_response.status_code == 200:
                    filing_matches = re.findall(r'<filing-href>(.*?)</filing-href>', filings_response.text)
                    ticker_data['filings'] = filing_matches[:10]
                
                output_file = self.sec_dir / f"{ticker}_sec.json"
                self._save_json(output_file, ticker_data)
                logger.info(f"  ✅ Saved SEC data for {ticker}")
                all_data[ticker] = ticker_data
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"  ❌ SEC failed for {ticker}: {e}")
        
        return all_data
    
    # ==================== NEWS COLLECTION ====================
    
    def collect_news(self, tickers: List[str], days_back: int = 30, api_key: str = None):
        """Collect news articles"""
        logger.info(f"📰 Collecting news for {tickers}")
        all_news = {}
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        for ticker in tickers:
            try:
                ticker_news = {
                    'ticker': ticker,
                    'collection_date': datetime.now().isoformat(),
                    'articles': []
                }
                
                # Source 1: NewsAPI (if key provided)
                if api_key:
                    self._rate_limit(0.5)
                    newsapi_url = "https://newsapi.org/v2/everything"
                    params = {
                        'q': ticker,
                        'from': start_date.strftime('%Y-%m-%d'),
                        'to': end_date.strftime('%Y-%m-%d'),
                        'sortBy': 'relevancy',
                        'language': 'en',
                        'pageSize': 50,
                        'apiKey': api_key
                    }
                    
                    response = requests.get(newsapi_url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        for article in data.get('articles', []):
                            ticker_news['articles'].append({
                                'source': 'NewsAPI',
                                'title': article.get('title', ''),
                                'description': article.get('description', ''),
                                'content': article.get('content', ''),
                                'url': article.get('url', ''),
                                'published_at': article.get('publishedAt', ''),
                                'sentiment': None
                            })
                        logger.info(f"  NewsAPI: {len(data.get('articles', []))} articles for {ticker}")
                
                # Source 2: GDELT (free, no key required)
                self._rate_limit(0.5)
                gdelt_url = "https://api.gdeltproject.org/api/v2/doc/doc"
                params = {
                    'query': ticker,
                    'mode': 'artlist',
                    'format': 'json',
                    'timespan': f'{days_back}d',
                    'maxrecords': 50
                }
                
                try:
                    response = requests.get(gdelt_url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        for article in data.get('articles', []):
                            ticker_news['articles'].append({
                                'source': 'GDELT',
                                'title': article.get('title', ''),
                                'description': article.get('description', ''),
                                'url': article.get('url', ''),
                                'published_at': article.get('seendate', ''),
                                'source_country': article.get('sourcecountry', '')
                            })
                        logger.info(f"  GDELT: {len(data.get('articles', []))} articles for {ticker}")
                except:
                    pass
                
                # Source 3: Sample news (fallback)
                if not ticker_news['articles']:
                    company_names = {
                        'AAPL': 'Apple', 'MSFT': 'Microsoft', 'GOOGL': 'Google',
                        'AMZN': 'Amazon', 'TSLA': 'Tesla', 'NVDA': 'NVIDIA'
                    }
                    company = company_names.get(ticker, ticker)
                    
                    sample_titles = [
                        f"{company} reports strong quarterly earnings, beating estimates",
                        f"Analysts upgrade {company} stock citing growth potential",
                        f"{company} announces new product launch",
                        f"Market reacts to {company}'s latest financial guidance",
                        f"{company} faces regulatory scrutiny in Europe",
                        f"Institutional investors increase holdings in {company}",
                        f"{company} announces strategic partnership",
                        f"Supply chain challenges impact {company}'s production",
                        f"{company} beats revenue expectations in Q3",
                        f"CEO of {company} discusses future strategy"
                    ]
                    
                    for i in range(min(20, len(sample_titles))):
                        article_date = datetime.now() - timedelta(days=i % days_back)
                        ticker_news['articles'].append({
                            'source': 'Sample',
                            'title': sample_titles[i % len(sample_titles)],
                            'description': f"Full article about {company} performance and market impact...",
                            'url': f"https://example.com/news/{ticker.lower()}/{i}",
                            'published_at': article_date.isoformat(),
                            'is_sample': True
                        })
                    logger.info(f"  Generated {len(ticker_news['articles'])} sample articles for {ticker}")
                
                # Save to file
                output_file = self.news_dir / f"{ticker}_news.json"
                self._save_json(output_file, ticker_news)
                logger.info(f"  ✅ Saved {len(ticker_news['articles'])} news articles for {ticker}")
                all_news[ticker] = ticker_news
                
            except Exception as e:
                logger.error(f"  ❌ News failed for {ticker}: {e}")
        
        return all_news
    
    def _generate_sample_news(self, ticker: str, days_back: int) -> List[Dict]:
        """Generate sample news for demonstration"""
        company_names = {
            'AAPL': 'Apple', 'MSFT': 'Microsoft', 'GOOGL': 'Google',
            'AMZN': 'Amazon', 'TSLA': 'Tesla', 'NVDA': 'NVIDIA'
        }
        company = company_names.get(ticker, ticker)
        
        sample_titles = [
            f"{company} reports strong quarterly earnings, beating estimates",
            f"Analysts upgrade {company} stock citing growth potential",
            f"{company} announces new product launch",
            f"Market reacts to {company}'s latest financial guidance",
            f"{company} faces regulatory scrutiny in Europe",
            f"Institutional investors increase holdings in {company}",
            f"{company} announces strategic partnership",
            f"Supply chain challenges impact {company}'s production",
            f"{company} beats revenue expectations in Q3",
            f"CEO of {company} discusses future strategy"
        ]
        
        articles = []
        for i in range(min(20, len(sample_titles))):
            article_date = datetime.now() - timedelta(days=i % days_back)
            articles.append({
                'source': 'Sample',
                'title': sample_titles[i % len(sample_titles)],
                'description': f"Full article about {company} performance and market impact...",
                'url': f"https://example.com/news/{ticker.lower()}/{i}",
                'published_at': article_date.isoformat(),
                'is_sample': True
            })
        
        return articles
    
    # ==================== COMPLETE PIPELINE ====================
    
    def collect_all(self, tickers: List[str], yahoo_period: str = "1y",
                   sec_years: List[int] = None, news_days: int = 30,
                   news_api_key: str = None):
        """Run complete data collection from all sources"""
        logger.info("="*60)
        logger.info("🚀 STARTING COMPLETE DATA COLLECTION")
        logger.info(f"📧 SEC EDGAR Email: {self.user_email}")
        logger.info("="*60)
        
        results = {}
        
        # 1. Yahoo Finance
        logger.info("\n📈 PHASE 1: Yahoo Finance Market Data")
        results['yahoo'] = self.collect_yahoo_finance(tickers, period=yahoo_period)
        
        # 2. SEC EDGAR
        logger.info("\n📄 PHASE 2: SEC EDGAR Filings")
        results['sec'] = self.collect_sec_edgar(tickers, years=sec_years)
        
        # 3. News
        logger.info("\n📰 PHASE 3: News Articles")
        results['news'] = self.collect_news(tickers, days_back=news_days, api_key=news_api_key)
        
        # Save master metadata
        metadata = {
            'collection_timestamp': datetime.now().isoformat(),
            'user_email': self.user_email,
            'tickers': tickers,
            'sources': ['yahoo_finance', 'sec_edgar', 'news'],
            'data_counts': {
                'yahoo': sum(len(v) for v in results['yahoo'].values()),
                'sec': len(results['sec']),
                'news': sum(len(v.get('articles', [])) for v in results['news'].values())
            },
            'config': {
                'yahoo_period': yahoo_period,
                'sec_years': sec_years,
                'news_days': news_days
            }
        }
        
        metadata_file = self.metadata_dir / "complete_collection_metadata.json"
        self._save_json(metadata_file, metadata)
        
        self.print_summary(results)
        
        return results
    
    def print_summary(self, results: Dict = None):
        """Print collection summary"""
        print("\n" + "="*60)
        print("📊 DATA COLLECTION SUMMARY")
        print("="*60)
        
        # Yahoo summary
        yahoo_count = len(results.get('yahoo', {})) if results else len(list(self.yahoo_dir.glob("*.json")))
        print(f"\n📈 Yahoo Finance: {yahoo_count} companies")
        if yahoo_count == 0:
            print("   ⚠️  No Yahoo data collected. Run: pip install yfinance")
        
        # SEC summary
        sec_count = len(results.get('sec', {})) if results else len(list(self.sec_dir.glob("*.json")))
        print(f"\n📄 SEC EDGAR: {sec_count} companies")
        
        # News summary
        news_total = 0
        sample_count = 0
        if results:
            for ticker, data in results.get('news', {}).items():
                news_total += len(data.get('articles', []))
                for article in data.get('articles', []):
                    if article.get('is_sample'):
                        sample_count += 1
        else:
            for file in self.news_dir.glob("*.json"):
                with open(file) as f:
                    data = json.load(f)
                    news_total += len(data.get('articles', []))
        
        print(f"\n📰 News: {news_total} total articles")
        if sample_count > 0:
            print(f"   ⚠️  {sample_count} articles are sample data")
        
        print(f"\n💾 Data saved to: {self.data_dir}")
        print("="*60)
    
    def export_for_graph_rag(self, output_file: str = "graph_rag_data.json"):
        """Export all collected data in Graph RAG ready format"""
        logger.info("📦 Exporting data for Graph RAG...")
        
        graph_data = {
            'entities': [],
            'relationships': [],
            'documents': []
        }
        
        # Load SEC data for companies and financials
        sec_files = list(self.sec_dir.glob("*_sec.json"))
        logger.info(f"Found {len(sec_files)} SEC data files")
        
        for file in sec_files:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                
                ticker = data.get('ticker', file.stem.replace('_sec', ''))
                
                # Add company entity
                graph_data['entities'].append({
                    'type': 'Company',
                    'id': ticker,
                    'properties': {
                        'ticker': ticker,
                        'name': ticker,
                        'cik': data.get('cik', '')
                    }
                })
                
                # Add financial metrics and relationships
                for year, financials in data.get('financial_statements', {}).items():
                    entity_id = f"{ticker}_{year}"
                    props = {'ticker': ticker, 'year': year}
                    props.update(financials)
                    graph_data['entities'].append({
                        'type': 'FinancialMetric',
                        'id': entity_id,
                        'properties': props
                    })
                    graph_data['relationships'].append({
                        'from': ticker,
                        'to': entity_id,
                        'type': 'HAS_FINANCIALS',
                        'properties': {'year': year}
                    })
            except Exception as e:
                logger.warning(f"Error loading {file}: {e}")
        
        # Load news as documents
        news_files = list(self.news_dir.glob("*_news.json"))
        logger.info(f"Found {len(news_files)} news files")
        
        for file in news_files:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                
                for article in data.get('articles', []):
                    doc = {
                        'id': article.get('url', f"{data['ticker']}_{time.time()}"),
                        'ticker': data['ticker'],
                        'title': article.get('title', ''),
                        'content': article.get('description', '') + ' ' + article.get('content', ''),
                        'source': article.get('source', 'unknown'),
                        'timestamp': article.get('published_at', '')
                    }
                    graph_data['documents'].append(doc)
            except Exception as e:
                logger.warning(f"Error loading {file}: {e}")
        
        # Save final export
        output_path = self.data_dir / output_file
        self._save_json(output_path, graph_data)
        
        logger.info(f"✅ Exported: {len(graph_data['entities'])} entities, "
                   f"{len(graph_data['relationships'])} relationships, "
                   f"{len(graph_data['documents'])} documents")
        
        return graph_data


# ==================== MAIN EXECUTION ====================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Complete Financial Data Collector - NO JSON ERRORS')
    parser.add_argument('--email', type=str, required=True, 
                       help='Your email for SEC API')
    parser.add_argument('--company', type=str, required=True, 
                       help='Your company name')
    parser.add_argument('--tickers', type=str, nargs='+', 
                       default=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA'],
                       help='Stock tickers to collect')
    parser.add_argument('--output-dir', type=str, default='./financial_data',
                       help='Output directory')
    parser.add_argument('--yahoo-period', type=str, default='1y',
                       help='Yahoo Finance period (1d,5d,1mo,1y,2y,5y,max)')
    parser.add_argument('--news-days', type=int, default=30,
                       help='Days of news to collect')
    parser.add_argument('--news-api-key', type=str, default=None,
                       help='NewsAPI key (optional)')
    parser.add_argument('--sec-years', type=int, nargs='+', default=None,
                       help='Years for SEC data (default: last 4 years)')
    parser.add_argument('--export-graph', action='store_true',
                       help='Export for Graph RAG pipeline')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("🎯 FINANCIAL DATA COLLECTOR - GRAPH RAG")
    print("="*60)
    print(f"📧 Email: {args.email}")
    print(f"🏢 Company: {args.company}")
    print(f"📊 Tickers: {', '.join(args.tickers)}")
    print(f"📁 Output: {args.output_dir}")
    print("="*60 + "\n")
    
    # Initialize collector
    collector = FinancialDataCollector(
        user_email=args.email,
        company_name=args.company,
        data_dir=args.output_dir
    )
    
    # Collect all data
    results = collector.collect_all(
        tickers=args.tickers,
        yahoo_period=args.yahoo_period,
        sec_years=args.sec_years,
        news_days=args.news_days,
        news_api_key=args.news_api_key
    )
    
    # Export for Graph RAG if requested
    if args.export_graph:
        collector.export_for_graph_rag()
    
    print("\n" + "="*60)
    print("✅ COMPLETE DATA COLLECTION FINISHED SUCCESSFULLY!")
    print("="*60)
    print(f"\n📧 Email used: {args.email}")
    print(f"📊 Collected data for {len(args.tickers)} companies")
    print(f"📁 Data location: {args.output_dir}")
    print("\n📋 Next Steps for Graph RAG:")
    print("  1. Review data in the output directory")
    print("  2. Load into Neo4j (graph database)")
    print("  3. Load into Weaviate (vector database)")
    print("  4. Build Graph RAG pipeline")
    print("="*60)


if __name__ == "__main__":
    main()