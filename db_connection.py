"""
Database connections for Neo4j and Weaviate
Graph RAG - Financial Insights Copilot
"""

import os
from neo4j import GraphDatabase
import weaviate
from weaviate.classes.init import Auth
import json
from pathlib import Path
import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConnector:
    """Handles connections to Neo4j and Weaviate"""

    def __init__(self):
        # ============================================
        # NEO4J CREDENTIALS (WORKING)
        # ============================================
        self.neo4j_uri        = os.environ.get("NEO4J_URI", "")
        self.neo4j_user       = os.environ.get("NEO4J_USER", "")
        self.neo4j_password   = os.environ.get("NEO4J_PASSWORD", "")
        self.weaviate_url     = os.environ.get("WEAVIATE_URL", "")
        self.weaviate_api_key = os.environ.get("WEAVIATE_API_KEY", "")
        self.openai_api_key   = os.environ.get("OPENAI_API_KEY", "")

        self.neo4j_driver = None
        self.weaviate_client = None

    # =========================
    # 🔌 NEO4J CONNECTION
    # =========================
    def connect_neo4j(self):
        try:
            self.neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
                connection_timeout=15,
                max_connection_lifetime=1000
            )

            with self.neo4j_driver.session() as session:
                session.run("RETURN 1").consume()

            logger.info("✅ Connected to Neo4j successfully!")
            return self.neo4j_driver

        except Exception as e:
            logger.error("❌ Neo4j Connection Failed")
            logger.error(e)
            self.neo4j_driver = None
            return None

    # =========================
    # 🔍 WEAVIATE CLOUD CONNECTION
    # =========================
    def connect_weaviate(self):
        try:
            # Using the updated method for Weaviate Cloud
            self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.weaviate_url,
                auth_credentials=Auth.api_key(self.weaviate_api_key),
                headers={
                    "X-OpenAI-Api-Key": self.openai_api_key
                }
            )

            if self.weaviate_client.is_ready():
                logger.info("✅ Connected to Weaviate Cloud successfully!")
                return self.weaviate_client
            else:
                logger.error("❌ Weaviate not ready")
                return None

        except Exception as e:
            logger.error(f"❌ Weaviate Connection Failed: {e}")
            return None

    # =========================
    # 📊 VERIFY NEO4J DATA
    # =========================
    def verify_neo4j_data(self):
        if not self.neo4j_driver:
            logger.error("❌ Neo4j not connected")
            return

        try:
            with self.neo4j_driver.session() as session:
                companies = session.run(
                    "MATCH (c:Company) RETURN count(c) AS count"
                ).single()["count"]

                metrics = session.run(
                    "MATCH (f:FinancialMetric) RETURN count(f) AS count"
                ).single()["count"]

                rels = session.run(
                    "MATCH ()-[r]->() RETURN count(r) AS count"
                ).single()["count"]

                print(f"\n📊 NEO4J VERIFICATION:")
                print(f"   🏢 Companies: {companies}")
                print(f"   💰 Financial Metrics: {metrics}")
                print(f"   🔗 Relationships: {rels}")

        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")

    # =========================
    # 📊 VERIFY WEAVIATE DATA
    # =========================
    def verify_weaviate_data(self):
        if not self.weaviate_client:
            logger.error("❌ Weaviate not connected")
            return

        try:
            if self.weaviate_client.collections.exists("FinancialDocument"):
                collection = self.weaviate_client.collections.get("FinancialDocument")
                response = collection.query.fetch_objects(limit=1)
                print(f"\n🔍 WEAVIATE VERIFICATION:")
                print(f"   📰 Collection: FinancialDocument exists")
                print(f"   📰 Sample documents: {len(response.objects)}")
            else:
                print(f"\n🔍 WEAVIATE VERIFICATION:")
                print(f"   📰 No collection yet")
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")

    # =========================
    # 📦 LOAD TO NEO4J
    # =========================
    def load_data_to_neo4j(self, data_file="./financial_data/graph_rag_data.json"):
        if not self.neo4j_driver:
            logger.error("❌ Neo4j not connected")
            return

        file_path = Path(data_file)
        if not file_path.exists():
            logger.error(f"❌ File not found: {data_file}")
            return

        with open(file_path, "r") as f:
            data = json.load(f)

        try:
            with self.neo4j_driver.session() as session:
                # Constraints
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE")
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:FinancialMetric) REQUIRE f.id IS UNIQUE")
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (n:News) REQUIRE n.id IS UNIQUE")

                # Companies
                for entity in data.get("entities", []):
                    if entity["type"] == "Company":
                        session.run(
                            "MERGE (c:Company {id: $id}) SET c += $props",
                            id=entity["id"],
                            props=entity["properties"]
                        )

                # Metrics
                for entity in data.get("entities", []):
                    if entity["type"] == "FinancialMetric":
                        session.run(
                            "MERGE (f:FinancialMetric {id: $id}) SET f += $props",
                            id=entity["id"],
                            props=entity["properties"]
                        )

                # Relationships
                for rel in data.get("relationships", []):
                    session.run(
                        f"MATCH (a {{id: $from_id}}), (b {{id: $to_id}}) "
                        f"MERGE (a)-[:{rel['type']}]->(b)",
                        from_id=rel["from"],
                        to_id=rel["to"]
                    )

                logger.info("✅ Data loaded into Neo4j")

        except Exception as e:
            logger.error(f"❌ Loading failed: {e}")

    # =========================
    # 📄 LOAD TO WEAVIATE
    # =========================
    def load_data_to_weaviate(self, data_file="./financial_data/graph_rag_data.json"):
        if not self.weaviate_client:
            logger.error("❌ Weaviate not connected")
            return

        file_path = Path(data_file)
        if not file_path.exists():
            logger.error(f"❌ File not found: {data_file}")
            return

        with open(file_path, "r") as f:
            data = json.load(f)

        try:
            # Delete existing collection if exists
            if self.weaviate_client.collections.exists("FinancialDocument"):
                self.weaviate_client.collections.delete("FinancialDocument")
                logger.info("🗑️ Deleted existing FinancialDocument collection")

            # Create new collection
            self.weaviate_client.collections.create(
                name="FinancialDocument",
                properties=[
                    weaviate.classes.config.Property(name="title", data_type=weaviate.classes.config.DataType.TEXT),
                    weaviate.classes.config.Property(name="ticker", data_type=weaviate.classes.config.DataType.TEXT),
                    weaviate.classes.config.Property(name="source", data_type=weaviate.classes.config.DataType.TEXT),
                    weaviate.classes.config.Property(name="timestamp", data_type=weaviate.classes.config.DataType.TEXT),
                ],
                vectorizer_config=weaviate.classes.config.Configure.Vectorizer.text2vec_openai()
            )
            logger.info("✅ Created FinancialDocument collection")

            collection = self.weaviate_client.collections.get("FinancialDocument")

            # Load documents
            doc_count = 0
            for doc in data.get("documents", []):
                collection.data.insert(
                    properties={
                        "title": doc.get("title", ""),
                        "ticker": doc.get("ticker", ""),
                        "source": doc.get("source", ""),
                        "timestamp": doc.get("timestamp", "")
                    }
                )
                doc_count += 1
                if doc_count % 20 == 0:
                    logger.info(f"   Loaded {doc_count} documents...")

            logger.info(f"✅ Loaded {doc_count} documents into Weaviate")

        except Exception as e:
            logger.error(f"❌ Weaviate error: {e}")

    # =========================
    # 🔒 CLOSE CONNECTIONS
    # =========================
    def close(self):
        if self.neo4j_driver:
            self.neo4j_driver.close()
            logger.info("🔒 Neo4j closed")

        if self.weaviate_client:
            self.weaviate_client.close()
            logger.info("🔒 Weaviate closed")


# =========================
# 🚀 MAIN RUN
# =========================
if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("🔌 DATABASE CONNECTION TEST")
    print("=" * 60)

    db = DatabaseConnector()

    # ==================== NEO4J ====================
    print("\n📊 STEP 1: Neo4j")
    if db.connect_neo4j():
        # Clear existing data? (optional)
        print("\n⚠️  Do you want to clear existing Neo4j data?")
        response = input("   Type 'yes' to clear, anything else to keep: ").strip().lower()
        
        if response == 'yes':
            with db.neo4j_driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            print("   🗑️ Cleared Neo4j database")
        
        db.load_data_to_neo4j()
        db.verify_neo4j_data()
    else:
        print("❌ Neo4j connection failed")

    # ==================== WEAVIATE ====================
    print("\n" + "=" * 60)
    print("🔍 STEP 2: Weaviate Cloud")
    print("=" * 60)

    if db.connect_weaviate():
        print("\n⚠️  Do you want to clear existing Weaviate data?")
        response = input("   Type 'yes' to clear, anything else to keep: ").strip().lower()
        
        if response == 'yes':
            if db.weaviate_client.collections.exists("FinancialDocument"):
                db.weaviate_client.collections.delete("FinancialDocument")
                print("   🗑️ Cleared Weaviate collection")
        
        db.load_data_to_weaviate()
        db.verify_weaviate_data()
    else:
        print("⚠️ Weaviate not connected - check your API keys")

    db.close()

    print("\n" + "=" * 60)
    print("✅ DATABASE OPERATIONS COMPLETE!")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("   1. Go to Neo4j Browser: MATCH (c:Company) RETURN c LIMIT 10")
    print("   2. Weaviate is ready for vector search")
    print("   3. Your Graph RAG system is ready!")
    print("=" * 60)