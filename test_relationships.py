from neo4j import GraphDatabase

URI = "neo4j+s://b1babcdd.databases.neo4j.io"
USER = "b1babcdd"
PASSWORD = "SFsLFG1f430yTdRVgqlIizxWXG4khrQkRTpbbhmEIIE"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

with driver.session() as session:
    # Check all SUPPLIES_TO relationships
    result = session.run("""
        MATCH (s)-[r:SUPPLIES_TO]->(c)
        RETURN s.id as supplier, c.id as customer
    """)
    
    print("SUPPLIES_TO relationships in Neo4j:")
    for record in result:
        print(f"  {record['supplier']} -> {record['customer']}")
    
    # Check suppliers for Apple
    result = session.run("""
        MATCH (supplier:Company)-[:SUPPLIES_TO]->(apple:Company {id: 'AAPL'})
        RETURN supplier.id as supplier
    """)
    
    print("\nSuppliers for AAPL:")
    for record in result:
        print(f"  {record['supplier']}")

driver.close()