"""Test script for MetadataManager functionality."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dbnotebook.core.metadata import MetadataManager


def test_metadata_manager():
    """Test MetadataManager operations."""
    print("=" * 60)
    print("Testing MetadataManager")
    print("=" * 60)

    # Initialize manager
    print("\n1. Initializing MetadataManager...")
    manager = MetadataManager(config_dir="data/config")

    # Get all practices
    print("\n2. Getting all IT Practices:")
    practices = manager.get_all_practices()
    for i, practice in enumerate(practices, 1):
        print(f"   {i}. {practice}")

    # Get all offerings
    print("\n3. Getting all Offerings:")
    offerings = manager.get_all_offerings()
    for offering in offerings:
        print(f"   - {offering['name']} ({offering['practice']})")
        print(f"     ID: {offering['id']}")
        print(f"     Description: {offering['description']}")

    # Get offerings by practice
    print("\n4. Getting offerings for 'Cloud Services':")
    cloud_offerings = manager.get_offerings_by_practice("Cloud Services")
    for offering in cloud_offerings:
        print(f"   - {offering['name']}")

    # Get statistics
    print("\n5. Metadata Statistics:")
    stats = manager.get_statistics()
    print(f"   Total Practices: {stats['total_practices']}")
    print(f"   Total Offerings: {stats['total_offerings']}")
    print(f"\n   Offerings by Practice:")
    for practice, count in stats['offerings_by_practice'].items():
        print(f"      {practice}: {count} offering(s)")

    # Test adding a new practice
    print("\n6. Testing add_practice():")
    success = manager.add_practice("Test Practice")
    print(f"   Added 'Test Practice': {success}")

    # Test adding a new offering
    print("\n7. Testing add_offering():")
    offering_id = manager.add_offering(
        practice="Cloud Services",
        offering_name="Test Offering",
        description="This is a test offering"
    )
    print(f"   Added 'Test Offering': {offering_id}")

    # Verify the additions
    print("\n8. Verifying additions:")
    practices = manager.get_all_practices()
    print(f"   Total practices now: {len(practices)}")

    cloud_offerings = manager.get_offerings_by_practice("Cloud Services")
    print(f"   Cloud Services offerings now: {len(cloud_offerings)}")

    print("\n" + "=" * 60)
    print("MetadataManager Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_metadata_manager()
