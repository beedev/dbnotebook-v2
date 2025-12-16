#!/usr/bin/env python
"""Test ChromaVectorStore initialization to reproduce the error."""

import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import TextNode

# Simulate our exact code path
chroma_client = chromadb.PersistentClient(path="data/chroma")
chroma_collection = chroma_client.get_or_create_collection(
    name="test_collection",
    metadata={"hnsw:space": "cosine"}
)

print("1. Creating ChromaVectorStore...")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
print(f"2. ChromaVectorStore created: {vector_store}")
print(f"3. Checking _collection attribute: {hasattr(vector_store, '_collection')}")

if hasattr(vector_store, '_collection'):
    print(f"4. _collection value: {vector_store._collection}")
else:
    print("ERROR: _collection attribute missing!")

print("5. Creating StorageContext...")
storage_context = StorageContext.from_defaults(vector_store=vector_store)

print("6. Creating test node...")
test_node = TextNode(
    id_="test-123",
    text="This is a test node",
    metadata={"test": "value"}
)

print("7. Creating VectorStoreIndex...")
try:
    index = VectorStoreIndex(
        nodes=[test_node],
        storage_context=storage_context
    )
    print("SUCCESS: VectorStoreIndex created!")
except Exception as e:
    print(f"ERROR creating VectorStoreIndex: {e}")
    import traceback
    traceback.print_exc()
