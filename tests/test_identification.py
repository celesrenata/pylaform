# test_identification.py
import os
import logging
from pylaform.database.templateWorker import Worker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure DYNAMODB_ENDPOINT_URL is set for local development
if 'DYNAMODB_ENDPOINT_URL' not in os.environ:
    os.environ['DYNAMODB_ENDPOINT_URL'] = 'http://localhost:8000'


def test_get_identification():
    """Test retrieving identification data"""
    worker = Worker()

    # Get all identification records
    identification = worker.get_identification()

    print(f"\nFound {len(identification)} identification records:")
    for item in identification:
        print(f"- {item.get('attr')}: {item.get('value')}")

    return identification


def test_update_identification():
    """Test updating an identification record"""
    worker = Worker()

    # Update an identification record
    updated = worker.update_identification(
        attr='name',
        value='Your Updated Name'
    )

    print(f"\nUpdate result: {'Success' if updated else 'Failed'}")

    # Get updated records to verify
    identification = worker.get_identification()

    print(f"\nVerifying updated records:")
    for item in identification:
        if item.get('attr') == 'name':
            print(f"- {item.get('attr')}: {item.get('value')}")


if __name__ == "__main__":
    print("Testing identification data functionality...\n")

    # Test retrieving identification data
    identification = test_get_identification()

    # Only test update if we found records
    if identification:
        test_update_identification()
    else:
        print("\nNo identification records found to update")