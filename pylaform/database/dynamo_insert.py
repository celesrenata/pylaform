import logging
import boto3
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_delay, wait_exponential
import os
import uuid
from pylaform.database.connect import db

logger = logging.getLogger(__name__)


class DynamoInserts:
    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def __init__(self, table=None):
        """
        Initialize the DynamoDB connection.

        :param table: Optional DynamoDB table object (for testing)
        """
        # Get table from connect.py
        self.table = table if table else db()

        # Define valid entities list that was missing
        self.valid_entities = ["summary", "school", "focus", "employer", "position",
                               "achievement", "skill", "certification", "glossary",
                               "IDENTIFICATION", "SUMMARY", "standalone_achievement"]

    def multi_column(self, entity_type, user_id=None, **data):
        """
        Insert a new record.

        :param str entity_type: The entity type
        :param str user_id: Optional user ID for multi-user support
        :param data: The data to insert
        :return: ID of the new record or None on failure
        """
        try:
            print(f"DEBUG: DynamoInserts.multi_column called for {entity_type}")
            print(f"DEBUG: Data to insert: {data}")
            print(f"DEBUG: User ID: {user_id}")

            # Validate entity type
            if entity_type not in self.valid_entities:
                print(f"DEBUG: Invalid entity type: {entity_type}")
                logger.error(f"Invalid entity type: {entity_type}")
                return None

            # Generate a new ID
            new_id = str(uuid.uuid4())
            print(f"DEBUG: Generated new ID: {new_id}")

            # Set default state if not provided
            if 'state' not in data:
                data['state'] = 1
                print("DEBUG: Added default state=1")

            # Add user_id if provided
            if user_id:
                data['user_id'] = user_id
                print(f"DEBUG: Added user_id={user_id}")

            # Prepare item with the composite key
            item = {
                'PK': f"{entity_type.upper()}",
                'SK': new_id,
                **data
            }
            print(f"DEBUG: Prepared item for insertion: {item}")

            # Handle special cases for relationships
            if entity_type == 'focus' and 'school_id' in data:
                print(f"DEBUG: Setting up GSI1 for focus with school_id {data['school_id']}")
                item['GSI1PK'] = f"SCHOOL#{data['school_id']}"
                item['GSI1SK'] = new_id
            elif entity_type == 'position' and 'employer_id' in data:
                print(f"DEBUG: Setting up GSI1 for position with employer_id {data['employer_id']}")
                item['GSI1PK'] = f"EMPLOYER#{data['employer_id']}"
                item['GSI1SK'] = data.get('startdate', new_id)
            elif entity_type == 'achievement' and 'position_id' in data:
                print(f"DEBUG: Setting up GSI1 for achievement with position_id {data['position_id']}")
                item['GSI1PK'] = f"POSITION#{data['position_id']}"
                item['GSI1SK'] = new_id

            # Add user GSI for faster user-specific queries if user_id is provided
            if user_id:
                print(f"DEBUG: Setting up GSI2 for user-specific queries with user_id {user_id}")
                item['GSI2PK'] = f"USER#{user_id}"
                item['GSI2SK'] = f"{entity_type.upper()}#{new_id}"

            # Insert the item
            print(f"DEBUG: Calling DynamoDB put_item")
            self.table.put_item(Item=item)
            print(f"DEBUG: Successfully inserted item with ID {new_id}")

            # Clear cache for this entity type
            if hasattr(self, 'purge_cache'):
                print(f"DEBUG: Purging cache for {entity_type}")
                self.purge_cache(entity_type, user_id)

            return new_id
        except Exception as e:
            print(f"DEBUG: Error in multi_column for {entity_type}: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            logger.error(f"Error inserting new {entity_type}: {str(e)}")
            return None

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def single_attr(self, entity_type: str, attr: str, value, user_id=None) -> str:
        """
        Insert a new record with a single attribute.

        :param str entity_type: The entity type
        :param str attr: Attribute name
        :param value: Attribute value
        :param str user_id: Optional user ID for multi-user support
        :return: ID of the new record or None on failure
        """
        return self.multi_column(entity_type, user_id=user_id, **{attr: value})

    def purge_cache(self, entity_type=None, user_id=None):
        """
        Purge the cache for a specific entity type and/or user.
        This is a stub method that will be replaced by the actual implementation
        when the cache is available.

        :param str entity_type: Optional entity type to purge
        :param str user_id: Optional user ID to purge
        """
        # This is just a stub - the actual implementation will be provided
        # by the class that has the cache (DynamoQueries)
        pass