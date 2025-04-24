from pymilvus import connections, Collection

# Assuming you have already established a connection to your Milvus server
connections.connect(host="localhost", port="19530")

collection_name = "insurance_customers"
try:
    collection = Collection(name=collection_name)
    collection.drop()
    print(f"Successfully dropped the collection: {collection_name}")
except Exception as e:
    print(f"Error dropping collection '{collection_name}': {e}")