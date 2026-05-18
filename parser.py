
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinancialDataParser:
    """Parse and extract financial data from SEC filings, news, and financial statements"""
    
    def __init__(self):
        # Financial metric patterns for extraction
        self.metric_patterns = {
            'revenue': r'(?:revenue|sales|turnover)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)\s*(?:billion|million|thousand)?',
            'net_income': r'(?:net income|net profit|earnings)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)\s*(?:billion|million|thousand)?',
            'total_assets': r'(?:total assets|assets)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)\s*(?:billion|million|thousand)?',
            'total_liabilities': r'(?:total liabilities|liabilities)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)\s*(?:billion|million|thousand)?',
            'cash_flow': r'(?:operating cash flow|cash from operations)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)\s*(?:billion|million|thousand)?',
            'eps': r'(?:earnings per share|EPS)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)',
            'pe_ratio': r'(?:P/E ratio|price to earnings)[:\s]*([0-9,]+(?:\.[0-9]+)?)',
            'dividend': r'(?:dividend|dividend per share)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)',
            'market_cap': r'(?:market capitalization|market cap)[:\s]*\$?([0-9,]+(?:\.[0-9]+)?)\s*(?:billion|million|trillion)?'
        }
        
        # Company name patterns
        self.company_patterns = {
            'AAPL': r'Apple\s*(?:Inc\.?|Computer|Corporation)?',
            'MSFT': r'Microsoft\s*(?:Corporation|Corp\.?)?',
            'GOOGL': r'Google|Alphabet\s*(?:Inc\.?)?',
            'AMZN': r'Amazon\s*(?:\.com|Inc\.?)?',
            'TSLA': r'Tesla\s*(?:Inc\.?|Motors)?',
            'NVDA': r'NVIDIA|Nvidia\s*(?:Corporation|Corp\.?)?'
        }
        
        # Date patterns
        self.date_patterns = [
            r'(\d{4})[-/](\d{2})[-/](\d{2})',  # YYYY-MM-DD
            r'(\d{2})[-/](\d{2})[-/](\d{4})',  # MM-DD-YYYY
            r'(\w+)\s+(\d{1,2}),\s+(\d{4})',   # Month DD, YYYY
        ]
    
    def extract_numbers(self, text: str) -> Dict[str, float]:
        """Extract numerical values from text"""
        numbers = {}
        
        for metric, pattern in self.metric_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(',', '')
                try:
                    value = float(value_str)
                    
                    # Handle billion/million suffixes
                    if 'billion' in match.group(0).lower():
                        value *= 1_000_000_000
                    elif 'million' in match.group(0).lower():
                        value *= 1_000_000
                    elif 'trillion' in match.group(0).lower():
                        value *= 1_000_000_000_000
                    
                    numbers[metric] = value
                except ValueError:
                    pass
        
        return numbers
    
    def extract_years(self, text: str) -> List[int]:
        """Extract years from text"""
        year_pattern = r'\b(20\d{2})\b'
        years = list(set(int(y) for y in re.findall(year_pattern, text)))
        return sorted(years)
    
    def extract_dates(self, text: str) -> List[str]:
        """Extract dates from text"""
        dates = []
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) == 3:
                    if int(match[0]) > 2000:  # YYYY-MM-DD format
                        dates.append(f"{match[0]}-{match[1]}-{match[2]}")
                    elif int(match[2]) > 2000:  # MM-DD-YYYY format
                        dates.append(f"{match[2]}-{match[0]}-{match[1]}")
        return list(set(dates))
    
    def extract_ticker(self, text: str) -> Optional[str]:
        """Extract ticker symbol from text"""
        ticker_pattern = r'\b([A-Z]{3,5})\b'
        matches = re.findall(ticker_pattern, text)
        # Filter common financial terms
        exclude = {'THE', 'AND', 'FOR', 'WITH', 'FROM', 'THIS', 'THAT', 'INC', 'LTD', 'CORP'}
        for match in matches:
            if match not in exclude:
                return match
        return None
    
    def parse_financial_statement(self, text: str, source: str = "sec") -> Dict:
        """Parse financial statement text into structured data"""
        
        result = {
            'metrics': self.extract_numbers(text),
            'years': self.extract_years(text),
            'dates': self.extract_dates(text),
            'ticker': self.extract_ticker(text),
            'source': source,
            'raw_text': text[:500]  # Store preview
        }
        
        # Organize metrics by year if possible
        organized_metrics = {}
        for year in result['years']:
            organized_metrics[year] = {}
            year_context = self.extract_context_around_year(text, year)
            organized_metrics[year] = self.extract_numbers(year_context)
        
        result['metrics_by_year'] = organized_metrics
        
        return result
    
    def extract_context_around_year(self, text: str, year: int, context_chars: int = 200) -> str:
        """Extract text around a specific year"""
        year_str = str(year)
        pos = text.find(year_str)
        if pos != -1:
            start = max(0, pos - context_chars)
            end = min(len(text), pos + context_chars)
            return text[start:end]
        return ""
    
    def parse_news_article(self, article: Dict) -> Dict:
        """Parse news article for financial insights"""
        
        title = article.get('title', '')
        description = article.get('description', '')
        content = f"{title} {description}"
        
        result = {
            'ticker': self.extract_ticker(content),
            'mentioned_companies': self.extract_company_names(content),
            'financial_metrics': self.extract_numbers(content),
            'sentiment_keywords': self.extract_sentiment_keywords(content),
            'dates': self.extract_dates(article.get('published_at', '')),
            'source': article.get('source', 'unknown'),
            'title': title,
            'url': article.get('url', '')
        }
        
        return result
    
    def extract_company_names(self, text: str) -> List[str]:
        """Extract company names from text"""
        companies = []
        for ticker, pattern in self.company_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                companies.append(ticker)
        return list(set(companies))
    
    def extract_sentiment_keywords(self, text: str) -> Dict[str, int]:
        """Extract sentiment-bearing keywords"""
        positive_keywords = ['profit', 'growth', 'increase', 'beat', 'positive', 'upgrade', 'strong', 'bullish']
        negative_keywords = ['loss', 'decline', 'decrease', 'miss', 'negative', 'downgrade', 'weak', 'bearish']
        
        text_lower = text.lower()
        
        positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in text_lower)
        
        return {
            'positive': positive_count,
            'negative': negative_count,
            'sentiment_score': (positive_count - negative_count) / (positive_count + negative_count + 1)
        }
    
    def parse_sec_filing(self, filing_data: Dict) -> Dict:
        """Parse SEC filing JSON data"""
        
        ticker = filing_data.get('ticker', '')
        financials = filing_data.get('financial_statements', {})
        
        parsed_financials = {}
        for year, metrics in financials.items():
            parsed_financials[year] = {
                'revenue': metrics.get('Revenue'),
                'net_income': metrics.get('NetIncome'),
                'total_assets': metrics.get('TotalAssets'),
                'total_liabilities': metrics.get('TotalLiabilities'),
                'operating_cash_flow': metrics.get('OperatingCashFlow')
            }
        
        return {
            'ticker': ticker,
            'cik': filing_data.get('cik', ''),
            'financials': parsed_financials,
            'num_years': len(parsed_financials),
            'collection_date': filing_data.get('collection_date', '')
        }
    
    def parse_yahoo_data(self, yahoo_data: Dict) -> Dict:
        """Parse Yahoo Finance data"""
        
        ticker = yahoo_data.get('ticker', '')
        company_info = yahoo_data.get('company_info', {})
        financials = yahoo_data.get('financials', {})
        
        return {
            'ticker': ticker,
            'company_name': company_info.get('name', ''),
            'sector': company_info.get('sector', ''),
            'industry': company_info.get('industry', ''),
            'market_cap': company_info.get('market_cap', 0),
            'pe_ratio': company_info.get('pe_ratio', 0),
            'beta': company_info.get('beta', 0),
            'financial_metrics': financials
        }
    
    def extract_financial_trends(self, financials: Dict) -> Dict:
        """Extract trends from financial data"""
        
        trends = {}
        years = sorted(financials.keys())
        
        if len(years) >= 2:
            for metric in ['revenue', 'net_income', 'total_assets']:
                values = []
                for year in years:
                    if financials[year].get(metric):
                        values.append(financials[year].get(metric))
                
                if len(values) >= 2:
                    trend = 'increasing' if values[-1] > values[0] else 'decreasing'
                    growth_rate = ((values[-1] - values[0]) / values[0]) * 100 if values[0] else 0
                    trends[metric] = {
                        'trend': trend,
                        'growth_rate': growth_rate,
                        'start_value': values[0],
                        'end_value': values[-1],
                        'start_year': years[0],
                        'end_year': years[-1]
                    }
        
        return trends
    
    def chunk_financial_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split financial text into overlapping chunks for vector storage"""
        
        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            if current_length + sentence_length <= chunk_size:
                current_chunk.append(sentence)
                current_length += sentence_length
            else:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                # Start new chunk with overlap
                overlap_sentences = current_chunk[-2:] if len(current_chunk) > 2 else current_chunk
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk)
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def prepare_for_graph_rag(self, parsed_data: Dict) -> Dict:
        """Prepare parsed data for Graph RAG pipeline"""
        
        return {
            'entities': self.extract_entities(parsed_data),
            'relationships': self.extract_relationships(parsed_data),
            'chunks': self.chunk_financial_text(parsed_data.get('raw_text', ''), 500, 50),
            'metadata': {
                'ticker': parsed_data.get('ticker'),
                'source': parsed_data.get('source'),
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def extract_entities(self, parsed_data: Dict) -> List[Dict]:
        """Extract entities for knowledge graph"""
        
        entities = []
        
        # Add company entity
        if parsed_data.get('ticker'):
            entities.append({
                'type': 'Company',
                'id': parsed_data['ticker'],
                'properties': {
                    'ticker': parsed_data['ticker'],
                    'name': parsed_data.get('company_name', parsed_data['ticker'])
                }
            })
        
        # Add financial metric entities
        for year, metrics in parsed_data.get('financials', {}).items():
            for metric_name, metric_value in metrics.items():
                if metric_value:
                    entities.append({
                        'type': 'FinancialMetric',
                        'id': f"{parsed_data.get('ticker')}_{year}_{metric_name}",
                        'properties': {
                            'ticker': parsed_data.get('ticker'),
                            'year': year,
                            'metric': metric_name,
                            'value': metric_value
                        }
                    })
        
        return entities
    
    def extract_relationships(self, parsed_data: Dict) -> List[Dict]:
        """Extract relationships for knowledge graph"""
        
        relationships = []
        ticker = parsed_data.get('ticker')
        
        if not ticker:
            return relationships
        
        for year, metrics in parsed_data.get('financials', {}).items():
            entity_id = f"{ticker}_{year}_revenue"
            relationships.append({
                'from': ticker,
                'to': entity_id,
                'type': 'HAS_FINANCIALS',
                'properties': {'year': year}
            })
        
        return relationships


# =========================
# MAIN EXECUTION
# =========================
def main():
    parser = FinancialDataParser()
    
    # Test with sample data
    sample_text = """
    Apple Inc. (AAPL) reported revenue of $383.3 billion for fiscal year 2023,
    with net income of $97.0 billion. Total assets reached $352.6 billion.
    The company's market capitalization is $2.8 trillion.
    """
    
    print("="*60)
    print("📊 FINANCIAL DATA PARSER TEST")
    print("="*60)
    
    # Parse sample text
    print("\n🔍 Parsing sample financial text:")
    print("-"*40)
    print(f"Input: {sample_text}")
    
    result = parser.parse_financial_statement(sample_text)
    print(f"\n📈 Extracted metrics: {result['metrics']}")
    print(f"📅 Extracted years: {result['years']}")
    print(f"🏷️ Extracted ticker: {result['ticker']}")
    
    # Parse sample article
    sample_article = {
        'title': 'Apple stock surges after strong earnings report',
        'description': 'AAPL shares rose 5% as company beats revenue estimates',
        'published_at': '2024-01-15',
        'source': 'Sample'
    }
    
    print("\n📰 Parsing sample news article:")
    print("-"*40)
    article_result = parser.parse_news_article(sample_article)
    print(f"🏷️ Ticker: {article_result['ticker']}")
    print(f"📊 Sentiment: {article_result['sentiment_keywords']}")
    
    print("\n✅ Parser test complete!")


if __name__ == "__main__":
    main()