"""
Graph RAG - Financial Insights Copilot
Hybrid mode: tries Neo4j + Weaviate first, falls back to local files.
"""

import os, json, csv, requests
from pathlib import Path
from typing import Dict, List, Optional
import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent

NAME_TO_TICKER = {
    'apple':'AAPL','aapl':'AAPL','microsoft':'MSFT','msft':'MSFT',
    'google':'GOOGL','alphabet':'GOOGL','googl':'GOOGL',
    'amazon':'AMZN','amzn':'AMZN','tesla':'TSLA','tsla':'TSLA',
    'nvidia':'NVDA','nvda':'NVDA','meta':'META','tsmc':'TSM',
    'samsung':'SSNLF','foxconn':'HNHPF','openai':'OPENAI',
    'rivian':'RIVN','lucid':'LCID','ford':'F',
}
TICKER_NAMES = {
    'AAPL':'Apple','MSFT':'Microsoft','GOOGL':'Alphabet','AMZN':'Amazon',
    'TSLA':'Tesla','NVDA':'NVIDIA','META':'Meta','TSM':'TSMC',
    'SSNLF':'Samsung','HNHPF':'Foxconn','OPENAI':'OpenAI',
    'RIVN':'Rivian','LCID':'Lucid','F':'Ford',
}


class GraphRAG:

    def __init__(self):
        self.neo4j_uri        = os.environ.get("NEO4J_URI", "")
        self.neo4j_user       = os.environ.get("NEO4J_USER", "")
        self.neo4j_password   = os.environ.get("NEO4J_PASSWORD", "")
        self.weaviate_url     = os.environ.get("WEAVIATE_URL", "")
        self.weaviate_api_key = os.environ.get("WEAVIATE_API_KEY", "")
        self.groq_api_key     = os.environ.get("GROQ_API_KEY", "")

        self.neo4j_driver   = None
        self.use_neo4j      = False
        self.use_weaviate   = False

        # local fallback data
        self._financials: Dict[str, List[Dict]] = {}
        self._relationships: List[Dict] = []
        self._news: Dict[str, List[Dict]] = {}
        self._companies: List[str] = []

    # ------------------------------------------------------------------
    # CONNECT
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        self._load_local_data()          # always load local as fallback

        # try Neo4j
        try:
            from neo4j import GraphDatabase
            self.neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
            )
            with self.neo4j_driver.session() as s:
                s.run("RETURN 1").consume()
            self.use_neo4j = True
            logger.info("Connected to Neo4j")
        except Exception as e:
            self.neo4j_driver = None
            self.use_neo4j = False
            logger.warning(f"Neo4j unavailable ({e}) — using local data")

        # try Weaviate (simple HTTP ping)
        try:
            r = requests.get(
                f"{self.weaviate_url}/v1/.well-known/ready",
                headers={"Authorization": f"Bearer {self.weaviate_api_key}"},
                timeout=6
            )
            self.use_weaviate = r.status_code == 200
            if self.use_weaviate:
                logger.info("Connected to Weaviate")
            else:
                logger.warning(f"Weaviate returned {r.status_code} — using local news")
        except Exception as e:
            self.use_weaviate = False
            logger.warning(f"Weaviate unavailable ({e}) — using local news")

        logger.info(f"Mode — Neo4j: {'cloud' if self.use_neo4j else 'local'} | "
                    f"Weaviate: {'cloud' if self.use_weaviate else 'local'}")
        return True

    # ------------------------------------------------------------------
    # LOCAL DATA LOADERS
    # ------------------------------------------------------------------

    def _load_local_data(self):
        self._load_financials()
        self._load_relationships()
        self._load_news()

    def _load_financials(self):
        try:
            sec_dir = BASE_DIR / "financial_data" / "sec_filings"
            if sec_dir.exists():
                for f in sec_dir.glob("*_sec.json"):
                    ticker = f.name.replace("_sec.json", "")
                    data = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
                    rows = []
                    for yr, vals in data.get("financial_statements", {}).items():
                        if not isinstance(vals, dict): continue
                        rows.append({
                            "year":         vals.get("year", int(yr)),
                            "revenue":      vals.get("GrossProfit"),
                            "net_income":   vals.get("NetIncome"),
                            "total_assets": vals.get("TotalAssets"),
                        })
                    rows.sort(key=lambda x: x["year"])
                    self._financials[ticker] = rows
                    if ticker not in self._companies:
                        self._companies.append(ticker)
        except Exception as e:
            logger.error(f"Local financials load error: {e}")

    def _load_relationships(self):
        try:
            rel_path = BASE_DIR / "relationships_data.csv"
            if not rel_path.exists(): return
            with open(rel_path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    fr = NAME_TO_TICKER.get(row["from_company"].strip().lower(), row["from_company"].strip().upper())
                    to = NAME_TO_TICKER.get(row["to_company"].strip().lower(),   row["to_company"].strip().upper())
                    self._relationships.append({"from": fr, "to": to, "type": row["relationship_type"].strip()})
        except Exception as e:
            logger.error(f"Local relationships load error: {e}")

    def _load_news(self):
        try:
            news_dir = BASE_DIR / "financial_data" / "news_data"
            if not news_dir.exists(): return
            for f in news_dir.glob("*_news.json"):
                ticker = f.name.replace("_news.json", "")
                data = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
                self._news[ticker] = data.get("articles", [])
        except Exception as e:
            logger.error(f"Local news load error: {e}")

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def format_currency(self, value):
        if not value or value == 0: return "N/A"
        try: return f"${float(value):,.0f}"
        except: return "N/A"

    def get_company_name(self, ticker: str) -> str:
        return TICKER_NAMES.get(ticker.upper(), ticker)

    # ------------------------------------------------------------------
    # COMPANIES
    # ------------------------------------------------------------------

    def get_all_companies(self) -> List[str]:
        if self.use_neo4j:
            try:
                with self.neo4j_driver.session() as s:
                    return [r["ticker"] for r in s.run("MATCH (c:Company) RETURN c.id as ticker")]
            except Exception as e:
                logger.warning(f"Neo4j get_all_companies failed: {e}")
        return self._companies or ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA"]

    # ------------------------------------------------------------------
    # FINANCIALS
    # ------------------------------------------------------------------

    def get_company_financials(self, ticker: str) -> Dict:
        ticker = ticker.upper()
        if self.use_neo4j:
            try:
                query = """
                MATCH (c:Company {id: $ticker})
                OPTIONAL MATCH (c)-[:HAS_FINANCIALS]->(f:FinancialMetric)
                RETURN c.id as ticker,
                       collect({year:f.year, revenue:f.Revenue,
                                net_income:f.NetIncome, total_assets:f.TotalAssets}) as financials
                """
                with self.neo4j_driver.session() as s:
                    rec = s.run(query, ticker=ticker).single()
                if rec:
                    fins = [f for f in rec["financials"] if f.get("year")]
                    fins.sort(key=lambda x: x.get("year", 0))
                    return {"ticker": ticker, "financials": fins}
            except Exception as e:
                logger.warning(f"Neo4j financials failed: {e}")
        # local fallback
        return {"ticker": ticker, "financials": self._financials.get(ticker, [])}

    # ------------------------------------------------------------------
    # WEAVIATE / NEWS
    # ------------------------------------------------------------------

    def search_weaviate(self, query: str, ticker: str = None, limit: int = 5) -> List[Dict]:
        if self.use_weaviate:
            try:
                where = ""
                if ticker:
                    where = f', where: {{operator: Equal, path: ["ticker"], valueString: "{ticker}"}}'
                gql = f'''{{ Get {{ FinancialDocument(limit: {limit}, nearText: {{concepts: ["{query}"]}}{where}) {{
                    title ticker source timestamp }} }} }}'''
                r = requests.post(
                    f"{self.weaviate_url}/v1/graphql",
                    headers={"Authorization": f"Bearer {self.weaviate_api_key}", "Content-Type": "application/json"},
                    json={"query": gql}, timeout=10
                )
                if r.status_code == 200:
                    return r.json().get("data", {}).get("Get", {}).get("FinancialDocument", [])
            except Exception as e:
                logger.warning(f"Weaviate search failed: {e}")
        # local fallback
        articles = self._news.get(ticker.upper(), []) if ticker else \
                   [a for arts in self._news.values() for a in arts]
        return [{"title": a.get("title",""), "ticker": ticker or "",
                 "source": a.get("source",""), "timestamp": a.get("published_at","")}
                for a in articles[:limit]]

    # ------------------------------------------------------------------
    # RELATIONSHIPS — Neo4j first, local fallback
    # ------------------------------------------------------------------

    def _neo4j_query_list(self, query: str, ticker: str, key: str) -> Optional[List[str]]:
        if not self.use_neo4j: return None
        try:
            with self.neo4j_driver.session() as s:
                return [r[key] for r in s.run(query, ticker=ticker.upper())]
        except Exception as e:
            logger.warning(f"Neo4j query failed: {e}")
            return None

    def get_suppliers(self, ticker: str) -> List[str]:
        result = self._neo4j_query_list(
            "MATCH (s:Company)-[:SUPPLIES_TO]->(c:Company {id:$ticker}) RETURN s.id as ticker",
            ticker, "ticker")
        if result is not None: return result
        t = ticker.upper()
        return [r["from"] for r in self._relationships if r["type"]=="SUPPLIES_TO" and r["to"]==t]

    def get_customers(self, ticker: str) -> List[str]:
        result = self._neo4j_query_list(
            "MATCH (c:Company {id:$ticker})-[:SUPPLIES_TO]->(cu:Company) RETURN cu.id as ticker",
            ticker, "ticker")
        if result is not None: return result
        t = ticker.upper()
        return [r["to"] for r in self._relationships if r["type"]=="SUPPLIES_TO" and r["from"]==t]

    def get_competitors(self, ticker: str) -> List[str]:
        result = self._neo4j_query_list(
            "MATCH (c:Company {id:$ticker})-[:COMPETES_WITH]-(o:Company) RETURN o.id as ticker",
            ticker, "ticker")
        if result is not None: return result
        t = ticker.upper()
        out = set()
        for r in self._relationships:
            if r["type"]=="COMPETES_WITH":
                if r["from"]==t: out.add(r["to"])
                elif r["to"]==t: out.add(r["from"])
        return list(out)

    def get_partners(self, ticker: str) -> List[str]:
        result = self._neo4j_query_list(
            "MATCH (c:Company {id:$ticker})-[:PARTNERS_WITH]-(o:Company) RETURN o.id as ticker",
            ticker, "ticker")
        if result is not None: return result
        t = ticker.upper()
        out = set()
        for r in self._relationships:
            if r["type"]=="PARTNERS_WITH":
                if r["from"]==t: out.add(r["to"])
                elif r["to"]==t: out.add(r["from"])
        return list(out)

    def get_related_companies(self, ticker: str, relationship_type: str = None) -> List[Dict]:
        if self.use_neo4j:
            try:
                if relationship_type:
                    q = f"MATCH (c:Company {{id:$ticker}})-[:{relationship_type}]->(o:Company) RETURN o.id as ticker, o.name as name, '{relationship_type}' as relationship"
                else:
                    q = "MATCH (c:Company {id:$ticker})-[r]->(o:Company) RETURN o.id as ticker, o.name as name, type(r) as relationship"
                with self.neo4j_driver.session() as s:
                    return [{"ticker":r["ticker"],"name":r.get("name",r["ticker"]),"relationship":r["relationship"]}
                            for r in s.run(q, ticker=ticker.upper())]
            except Exception as e:
                logger.warning(f"Neo4j related companies failed: {e}")
        t = ticker.upper()
        out = []
        for r in self._relationships:
            if relationship_type and r["type"]!=relationship_type: continue
            if r["from"]==t:
                out.append({"ticker":r["to"],"name":self.get_company_name(r["to"]),"relationship":r["type"]})
            elif r["to"]==t and r["type"] in ("COMPETES_WITH","PARTNERS_WITH"):
                out.append({"ticker":r["from"],"name":self.get_company_name(r["from"]),"relationship":r["type"]})
        return out

    # ------------------------------------------------------------------
    # GROQ LLM
    # ------------------------------------------------------------------

    def get_groq_answer(self, prompt: str) -> str:
        if not self.groq_api_key: return "Groq API key not configured."
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.groq_api_key}", "Content-Type": "application/json"},
                json={"model":"llama-3.1-8b-instant",
                      "messages":[{"role":"system","content":"You are a financial analyst. Be concise and data-driven."},
                                  {"role":"user","content":prompt}],
                      "temperature":0.3,"max_tokens":500},
                timeout=30
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            return f"Groq error {r.status_code}: {r.text[:200]}"
        except Exception as e:
            return f"Groq error: {e}"

    # ------------------------------------------------------------------
    # ASK METHODS
    # ------------------------------------------------------------------

    def analyze_impact_propagation(self, ticker: str, issue: str) -> str:
        suppliers=self.get_suppliers(ticker); customers=self.get_customers(ticker)
        competitors=self.get_competitors(ticker); partners=self.get_partners(ticker)
        result = f"Impact Analysis: {ticker} facing '{issue}'\n\n"
        if suppliers:   result += f"Suppliers impacted: {', '.join(suppliers)}\n\n"
        if customers:   result += f"Customers impacted: {', '.join(customers)}\n\n"
        if competitors: result += f"Competitors that may benefit: {', '.join(competitors)}\n\n"
        if partners:    result += f"Partners affected: {', '.join(partners)}\n"
        if not any([suppliers,customers,competitors,partners]):
            return f"No relationship data for {ticker}."
        return result

    def ask_impact(self, company: str, issue: str) -> str:
        company = company.upper()
        fins = self.get_company_financials(company)["financials"]
        fin_summary = ""
        for f in fins[-3:]:
            yr = f.get("year","N/A")
            rev = self.format_currency(f.get("revenue")); ni = self.format_currency(f.get("net_income"))
            if rev!="N/A" or ni!="N/A":
                fin_summary += f"Year {yr}: Revenue={rev}, Net Income={ni}\n"
        if not fin_summary: fin_summary = "Limited financial data available"

        suppliers=self.get_suppliers(company); customers=self.get_customers(company); competitors=self.get_competitors(company)
        rel = ""
        if customers:   rel += f"\n{company} supplies to: {', '.join(self.get_company_name(c) for c in customers)}"
        if suppliers:   rel += f"\nSuppliers: {', '.join(self.get_company_name(s) for s in suppliers)}"
        if competitors: rel += f"\nCompetitors: {', '.join(self.get_company_name(c) for c in competitors)}"

        return self.get_groq_answer(f"""You are a financial analyst. Analyze impact of "{issue}" on {company}.
Financial Data:\n{fin_summary}
Business Relationships:{rel if rel else " None available"}
Provide 3-4 sentence analysis: financial impact, relationship impact, recommendation.""")

    def ask_general(self, query: str, ticker: str = None) -> str:
        if ticker: ticker = ticker.upper()
        ql = query.lower()

        if ticker:
            if any(w in ql for w in ["supplier","supplies to","who provides"]):
                s = self.get_suppliers(ticker)
                if s: return self.get_groq_answer(f"One sentence: Who supplies to {ticker}? Suppliers: {', '.join(self.get_company_name(x) for x in s)}")
                return f"No supplier data for {ticker}."
            if any(w in ql for w in ["customer","supply to","whom does","sells to"]):
                c = self.get_customers(ticker)
                if c: return self.get_groq_answer(f"One sentence: Whom does {ticker} supply to? Customers: {', '.join(self.get_company_name(x) for x in c)}")
                return f"No customer data for {ticker}."
            if any(w in ql for w in ["competitor","compete","rival"]):
                c = self.get_competitors(ticker)
                if c: return self.get_groq_answer(f"One sentence: Who competes with {ticker}? Competitors: {', '.join(self.get_company_name(x) for x in c)}")
                return f"No competitor data for {ticker}."
            if "partner" in ql:
                p = self.get_partners(ticker)
                if p: return self.get_groq_answer(f"One sentence: Who are {ticker}'s partners? Partners: {', '.join(self.get_company_name(x) for x in p)}")
                return f"No partner data for {ticker}."
            if any(w in ql for w in ["affect","impact","propagation","who would be"]):
                return self.analyze_impact_propagation(ticker, query)

        context = ""
        if ticker:
            fins = self.get_company_financials(ticker)["financials"]
            if fins:
                context += f"\nFinancial data for {ticker}:\n"
                for f in fins[-4:]:
                    context += f"Year {f.get('year','N/A')}: Revenue={self.format_currency(f.get('revenue'))}, Net Income={self.format_currency(f.get('net_income'))}, Assets={self.format_currency(f.get('total_assets'))}\n"
        news = self.search_weaviate(query, ticker, limit=3)
        if news:
            context += "\nRelevant news:\n" + "".join(f"- {n.get('title','')}\n" for n in news[:3])
        if not context:
            return f"No data available for {ticker or 'this query'}."

        return self.get_groq_answer(f"Answer using ONLY this data.\nQuestion: {query}\nData:\n{context}\nBe concise, include numbers. Answer:")

    def close(self):
        if self.neo4j_driver:
            try: self.neo4j_driver.close()
            except: pass
        logger.info("GraphRAG closed")

    # legacy chat method
    def chat(self):
        rag = self
        print("\nFINANCIAL INSIGHTS COPILOT\nType 'quit' to exit\n")
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() == "quit": break
            if "ticker:" in user_input.lower():
                parts = user_input.lower().split("ticker:")
                q = parts[0].replace("ask","").strip(); t = parts[1].strip().upper()
                print(rag.ask_general(q, t))
            elif user_input.lower().startswith("impact"):
                parts = user_input[7:].split("|")
                if len(parts)>=2: print(rag.ask_impact(parts[0].strip().upper(), parts[1].strip()))
            elif user_input.lower().startswith("ask"):
                print(rag.ask_general(user_input[4:].strip()))
            elif user_input.lower()=="list":
                print(", ".join(rag.get_all_companies()))


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--ask"); p.add_argument("--ticker"); p.add_argument("--impact")
    p.add_argument("--relationships"); p.add_argument("--list", action="store_true")
    args = p.parse_args()
    rag = GraphRAG()
    rag.connect()
    if args.list:       print(rag.get_all_companies())
    elif args.impact:
        parts = args.impact.split("|")
        if len(parts)>=2: print(rag.ask_impact(parts[0].strip().upper(), parts[1].strip()))
    elif args.ask:      print(rag.ask_general(args.ask, args.ticker))
    rag.close()

if __name__ == "__main__":
    main()
