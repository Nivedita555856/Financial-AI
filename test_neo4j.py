from neo4j import GraphDatabase

URI = "neo4j+s://b1babcdd.databases.neo4j.io"
USER = "b1babcdd"
PASSWORD = "SFsLFG1f430yTdRVgqlIizxWXG4khrQkRTpbbhmEIIE"

print("Testing Neo4j connection...")
print(f"URI: {URI}")
print(f"User: {USER}")

try:
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    driver.verify_connectivity()
    print("✅ SUCCESS! Connected to Neo4j!")
    
    with driver.session() as session:
        result = session.run("RETURN 'Connected!' AS message")
        print(result.single()["message"])
    
    driver.close()
    
except Exception as e:
    print(f"❌ FAILED: {e}")