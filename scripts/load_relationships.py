"""
Load relationship data into Neo4j
Run this file separately - does not affect existing code
"""

from neo4j import GraphDatabase
import csv
from pathlib import Path

# Neo4j Credentials (same as your existing)
NEO4J_URI = "neo4j+s://b1babcdd.databases.neo4j.io"
NEO4J_USER = "b1babcdd"
NEO4J_PASSWORD = "SFsLFG1f430yTdRVgqlIizxWXG4khrQkRTpbbhmEIIE"

# Company name to ticker mapping
NAME_TO_TICKER = {
    'Apple': 'AAPL',
    'Microsoft': 'MSFT',
    'Google': 'GOOGL',
    'Amazon': 'AMZN',
    'Tesla': 'TSLA',
    'NVIDIA': 'NVDA',
    'TSMC': 'TSM',
    'Samsung': 'SSNLF',
    'Foxconn': 'HNHPF',
    'OpenAI': 'OPENAI',
    'Rivian': 'RIVN',
    'Lucid': 'LCID',
    'Panasonic': 'PCRFY'
}

def load_relationships():
    """Load relationships from CSV file into Neo4j"""
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    csv_path = Path(__file__).parent / "relationships_data.csv"
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        return
    
    print("Loading relationships into Neo4j...")
    
    with driver.session() as session:
        # First, ensure all company nodes exist
        for name, ticker in NAME_TO_TICKER.items():
            session.run(
                "MERGE (c:Company {id: $ticker}) SET c.name = $name",
                ticker=ticker, name=name
            )
        print("Company nodes verified")
        
        # Load relationships from CSV
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            count = 0
            
            for row in reader:
                from_name = row['from_company']
                to_name = row['to_company']
                rel_type = row['relationship_type']
                
                from_ticker = NAME_TO_TICKER.get(from_name)
                to_ticker = NAME_TO_TICKER.get(to_name)
                
                if from_ticker and to_ticker:
                    result = session.run(
                        f"""
                        MATCH (a:Company {{id: $from_ticker}})
                        MATCH (b:Company {{id: $to_ticker}})
                        MERGE (a)-[:{rel_type}]->(b)
                        RETURN a.id as from_id, b.id as to_id
                        """,
                        from_ticker=from_ticker, to_ticker=to_ticker
                    )
                    if result.single():
                        print(f"  Added: {from_name}({from_ticker}) -[:{rel_type}]-> {to_name}({to_ticker})")
                        count += 1
                    else:
                        print(f"  Failed: {from_name} or {to_name} not found")
                else:
                    print(f"  Skipped: {from_name} -> {to_name} (ticker mapping missing)")
        
        print(f"\nLoaded {count} relationships into Neo4j")
    
    driver.close()
    print("Done!")

def verify_relationships():
    """Verify loaded relationships"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Company)-[r]->(related:Company)
            RETURN c.id as from_ticker, type(r) as relationship, related.id as to_ticker
            LIMIT 20
        """)
        
        print("\nVerifying relationships in Neo4j:")
        for record in result:
            print(f"  {record['from_ticker']} -[{record['relationship']}]-> {record['to_ticker']}")
    
    driver.close()

if __name__ == "__main__":
    load_relationships()
    verify_relationships()