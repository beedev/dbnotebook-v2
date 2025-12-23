"""Test script for Phase 2: Retrieval & Filtering functionality."""
import sys
from pathlib import Path
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from llama_index.core.schema import Document, TextNode
from dbnotebook.core.ingestion import LocalDataIngestion
from dbnotebook.core.vector_store import LocalVectorStore
from dbnotebook.core.engine.retriever import LocalRetriever
from dbnotebook.core.metadata import MetadataManager
from dbnotebook.core.model import LocalRAGModel
from dbnotebook.setting import get_settings


def create_test_documents() -> List[Document]:
    """Create test documents with different metadata."""
    documents = [
        Document(
            text="Cloud migration services help organizations move to AWS, Azure, and GCP. We provide assessment, planning, and execution.",
            metadata={
                "file_name": "cloud_migration_doc.txt",
                "it_practice": "Cloud Services",
                "offering_name": "Cloud Migration",
                "offering_id": "cloud-001"
            }
        ),
        Document(
            text="Digital transformation involves modernizing legacy systems, implementing new digital channels, and improving customer experiences.",
            metadata={
                "file_name": "digital_transform_doc.txt",
                "it_practice": "Digital Transformation",
                "offering_name": "Digital Experience Platform",
                "offering_id": "digital-001"
            }
        ),
        Document(
            text="Cybersecurity assessment identifies vulnerabilities, reviews security policies, and recommends improvements for compliance.",
            metadata={
                "file_name": "security_doc.txt",
                "it_practice": "Cybersecurity",
                "offering_name": "Security Assessment",
                "offering_id": "security-001"
            }
        ),
        Document(
            text="Cloud optimization reduces costs through right-sizing, reserved instances, and automated resource management.",
            metadata={
                "file_name": "cloud_optimization_doc.txt",
                "it_practice": "Cloud Services",
                "offering_name": "Cloud Optimization",
                "offering_id": "cloud-002"
            }
        ),
        Document(
            text="Data analytics platform implementation enables business intelligence, predictive analytics, and data visualization.",
            metadata={
                "file_name": "data_analytics_doc.txt",
                "it_practice": "Data & Analytics",
                "offering_name": "Analytics Platform",
                "offering_id": "data-001"
            }
        )
    ]
    return documents


def test_metadata_filtering():
    """Test metadata-based filtering in retrieval."""
    print("=" * 60)
    print("Testing Phase 2: Retrieval & Filtering")
    print("=" * 60)

    # Initialize components
    print("\n1. Initializing components...")
    settings = get_settings()
    metadata_mgr = MetadataManager(config_dir="data/config")
    vector_store = LocalVectorStore(persist=False, setting=settings)  # Use in-memory for testing
    ingestion = LocalDataIngestion(setting=settings, use_cache=False)
    retriever_factory = LocalRetriever(setting=settings)

    # Create test documents
    print("\n2. Creating test documents...")
    documents = create_test_documents()
    print(f"   Created {len(documents)} test documents")

    # Convert documents to nodes
    print("\n3. Converting documents to nodes...")
    from llama_index.core.node_parser import SentenceSplitter
    splitter = SentenceSplitter.from_defaults(
        chunk_size=settings.ingestion.chunk_size,
        chunk_overlap=settings.ingestion.chunk_overlap
    )
    nodes = splitter(documents)
    print(f"   Created {len(nodes)} nodes from documents")

    # Display node metadata
    print("\n4. Node metadata summary:")
    practice_counts = {}
    for node in nodes:
        practice = node.metadata.get("it_practice", "Unknown")
        practice_counts[practice] = practice_counts.get(practice, 0) + 1

    for practice, count in sorted(practice_counts.items()):
        print(f"   {practice}: {count} node(s)")

    # Test filtering by IT Practice
    print("\n5. Testing filtering by IT Practice...")

    # Filter for Cloud Services
    print("\n   a) Filtering for 'Cloud Services':")
    cloud_index = vector_store.get_index_with_filter(
        nodes=nodes,
        practice_names=["Cloud Services"]
    )
    if cloud_index:
        cloud_nodes = cloud_index.docstore.docs
        print(f"      Found {len(cloud_nodes)} nodes for Cloud Services")
        for node_id, node in list(cloud_nodes.items())[:2]:  # Show first 2
            offering = node.metadata.get("offering_name", "N/A")
            print(f"      - {offering}: {node.text[:80]}...")

    # Filter for Cybersecurity
    print("\n   b) Filtering for 'Cybersecurity':")
    security_index = vector_store.get_index_with_filter(
        nodes=nodes,
        practice_names=["Cybersecurity"]
    )
    if security_index:
        security_nodes = security_index.docstore.docs
        print(f"      Found {len(security_nodes)} nodes for Cybersecurity")
        for node_id, node in list(security_nodes.items())[:2]:
            offering = node.metadata.get("offering_name", "N/A")
            print(f"      - {offering}: {node.text[:80]}...")

    # Test filtering by Offering ID
    print("\n6. Testing filtering by Offering ID...")

    # Filter for cloud-001
    print("\n   a) Filtering for offering 'cloud-001':")
    cloud_migration_index = vector_store.get_index_with_filter(
        nodes=nodes,
        offering_ids=["cloud-001"]
    )
    if cloud_migration_index:
        cloud_migration_nodes = cloud_migration_index.docstore.docs
        print(f"      Found {len(cloud_migration_nodes)} nodes for cloud-001")
        for node_id, node in list(cloud_migration_nodes.items())[:2]:
            print(f"      - {node.text[:80]}...")

    # Test multiple offering IDs (OR operation)
    print("\n   b) Filtering for multiple offerings ['cloud-001', 'security-001']:")
    multi_offering_index = vector_store.get_index_with_filter(
        nodes=nodes,
        offering_ids=["cloud-001", "security-001"]
    )
    if multi_offering_index:
        multi_nodes = multi_offering_index.docstore.docs
        print(f"      Found {len(multi_nodes)} nodes for multiple offerings")
        for node_id, node in list(multi_nodes.items())[:3]:
            offering = node.metadata.get("offering_name", "N/A")
            print(f"      - {offering}: {node.text[:60]}...")

    # Test no matches
    print("\n7. Testing edge case: No matching nodes...")
    no_match_index = vector_store.get_index_with_filter(
        nodes=nodes,
        offering_ids=["non-existent-offering"]
    )
    if no_match_index is None:
        print("   ✓ Correctly returned None for non-existent offering")
    else:
        print("   ✗ Expected None but got an index")

    # Test retriever with filtering
    print("\n8. Testing retriever with offering filter...")
    try:
        # Initialize LLM (required for retriever)
        llm = LocalRAGModel(setting=settings).get_llm()

        # Test retriever with Cloud Services filter
        retriever = retriever_factory.get_retrievers(
            llm=llm,
            language="eng",
            nodes=nodes,
            practice_filter=["Cloud Services"],
            vector_store=vector_store
        )
        print("   ✓ Successfully created retriever with practice filter")

        # Test retriever with offering filter
        retriever_offering = retriever_factory.get_retrievers(
            llm=llm,
            language="eng",
            nodes=nodes,
            offering_filter=["cloud-001", "data-001"],
            vector_store=vector_store
        )
        print("   ✓ Successfully created retriever with offering filter")

    except Exception as e:
        print(f"   ✗ Error creating retriever: {e}")

    # Test statistics
    print("\n9. Testing metadata statistics...")
    stats = metadata_mgr.get_statistics()
    print(f"   Total IT Practices: {stats['total_practices']}")
    print(f"   Total Offerings: {stats['total_offerings']}")

    print("\n" + "=" * 60)
    print("Phase 2 Filtering Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_metadata_filtering()
