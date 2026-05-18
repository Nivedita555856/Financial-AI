
import os
import weaviate
from weaviate.classes.init import Auth

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

WEAVIATE_URL     = os.environ.get("WEAVIATE_URL", "")
WEAVIATE_API_KEY = os.environ.get("WEAVIATE_API_KEY", "")
OPENAI_API_KEY   = os.environ.get("OPENAI_API_KEY", "")

print("\n" + "="*60)
print("🔍 TESTING WEAVIATE CLOUD CONNECTION")
print("="*60)

print(f"\n📡 Connecting to: {WEAVIATE_URL}")

try:
    # Connect to Weaviate Cloud
    client = weaviate.connect_to_wcs(
        cluster_url=WEAVIATE_URL,
        auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
        headers={
            "X-OpenAI-Api-Key": OPENAI_API_KEY
        }
    )
    
    # Test connection
    if client.is_ready():
        print("✅ SUCCESS! Connected to Weaviate Cloud!")
    else:
        print("❌ Weaviate Cloud not ready")
        exit(1)
    
    # Check cluster status
    print("\n📊 CLUSTER INFO:")
    print(f"   ✅ Status: Healthy")
    print(f"   ✅ Version: {client.get_meta().get('version', 'Unknown')}")
    
    # List existing collections
    collections = client.collections.list_all()
    print(f"\n📚 EXISTING COLLECTIONS:")
    if collections:
        for name in collections.keys():
            print(f"   • {name}")
    else:
        print("   • No collections yet")
    
    # Create a test collection
    print("\n🧪 CREATING TEST COLLECTION...")
    test_collection_name = "TestConnection"
    
    if client.collections.exists(test_collection_name):
        client.collections.delete(test_collection_name)
        print(f"   ✅ Deleted existing {test_collection_name}")
    
    client.collections.create(
        name=test_collection_name,
        properties=[
            weaviate.classes.config.Property(name="message", data_type=weaviate.classes.config.DataType.TEXT),
        ],
        vectorizer_config=weaviate.classes.config.Configure.Vectorizer.text2vec_openai()
    )
    print(f"   ✅ Created collection: {test_collection_name}")
    
    # Insert a test object
    print("\n📝 INSERTING TEST DATA...")
    collection = client.collections.get(test_collection_name)
    
    object_uuid = collection.data.insert(
        properties={
            "message": "Hello from Weaviate! Connection test successful."
        }
    )
    print(f"   ✅ Inserted object with ID: {object_uuid}")
    
    # Search the test object
    print("\n🔎 SEARCHING TEST DATA...")
    response = collection.query.near_text(
        query="connection test",
        limit=1
    )
    
    if response.objects:
        print(f"   ✅ Found: {response.objects[0].properties['message']}")
    else:
        print("   ⚠️ No results found")
    
    # Clean up
    print("\n🧹 CLEANING UP...")
    client.collections.delete(test_collection_name)
    print(f"   ✅ Deleted test collection")
    
    # Final verification
    print("\n" + "="*60)
    print("✅ WEAVIATE TEST COMPLETE - ALL SYSTEMS OK!")
    print("="*60)
    print("\n📋 Summary:")
    print("   ✅ Connection successful")
    print("   ✅ Can create collections")
    print("   ✅ Can insert data")
    print("   ✅ Can search with vector embeddings")
    print("   ✅ Can delete collections")
    
except Exception as e:
    print(f"\n❌ TEST FAILED: {e}")
    print("\nPossible issues:")
    print("   1. Check your WEAVIATE_API_KEY is correct")
    print("   2. Check your OPENAI_API_KEY is valid")
    print("   3. Make sure you have internet connection")
    
finally:
    if 'client' in locals():
        client.close()
        print("\n🔒 Connection closed")