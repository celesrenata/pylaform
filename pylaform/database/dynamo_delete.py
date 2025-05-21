import logging
import boto3
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_delay, wait_exponential
import os
from pylaform.database.connect import db

logger = logging.getLogger(__name__)


class DynamoDeletes:
    """
    Handle all DynamoDB delete operations with proper error handling.
    """

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def __init__(self, table=None):
        """
        Initialize the DynamoDB connection.

        :param table: Optional DynamoDB table object (for testing)
        """
        # Get table from connect.py
        self.table = table if table else db()

        # Define valid entities list
        self.valid_entities = ["summary", "school", "focus", "employer", "position",
                               "achievement", "skill", "certification", "glossary",
                               "standalone_achievement", "IDENTIFICATION", "SUMMARY"]

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def record(self, entity_type, record_id, user_id=None):
        """
        Delete a record from DynamoDB.

        :param str entity_type: The entity type
        :param str record_id: ID of the record to delete
        :param str user_id: Optional user ID for multi-user support
        :return: True if successful, False otherwise
        """
        try:
            print(f"DEBUG: DynamoDeletes.record called for {entity_type} with ID {record_id}, user_id={user_id}")

            # Validate entity type
            if entity_type not in self.valid_entities:
                logger.error(f"Invalid entity type: {entity_type}")
                print(f"DEBUG: Invalid entity type: {entity_type}")
                return False

            # If user_id is provided, verify the record belongs to this user
            if user_id:
                print(f"DEBUG: Verifying record belongs to user {user_id}")
                try:
                    # Get the item first to check ownership
                    response = self.table.get_item(
                        Key={
                            'PK': f"{entity_type.upper()}",
                            'SK': str(record_id)
                        }
                    )

                    if 'Item' not in response:
                        logger.error(f"Record {entity_type}/{record_id} not found")
                        print(f"DEBUG: Record {entity_type}/{record_id} not found")
                        return False

                    item = response['Item']
                    if 'user_id' in item and item['user_id'] != user_id:
                        logger.error(f"Record {entity_type}/{record_id} belongs to a different user")
                        print(f"DEBUG: Record {entity_type}/{record_id} belongs to a different user")
                        return False

                    print(f"DEBUG: Record ownership verified for user {user_id}")
                except Exception as e:
                    logger.error(f"Error verifying record ownership: {str(e)}")
                    print(f"DEBUG: Error verifying record ownership: {str(e)}")
                    return False

            # Delete the item
            print(f"DEBUG: Deleting record {entity_type}/{record_id}")
            self.table.delete_item(
                Key={
                    'PK': f"{entity_type.upper()}",
                    'SK': str(record_id)
                }
            )

            logger.info(f"Deleted {entity_type} record with ID {record_id}")
            print(f"DEBUG: Successfully deleted {entity_type} record with ID {record_id}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting {entity_type} record {record_id}: {str(e)}")
            print(f"DEBUG: Error deleting {entity_type} record {record_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in record deletion: {str(e)}")
            print(f"DEBUG: Unexpected error in record deletion: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            return False

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def delete_entry(self, entity_type, record_id, hard_delete=False, user_id=None):
        """
        Delete an entry using either hard or soft delete.

        :param str entity_type: The entity type
        :param str record_id: ID of the record to delete
        :param bool hard_delete: True for permanent deletion, False for soft delete
        :param str user_id: Optional user ID for multi-user support
        :return: True if successful, False otherwise
        """
        try:
            print(
                f"DEBUG: DynamoDeletes.delete_entry called for {entity_type} with ID {record_id}, hard_delete={hard_delete}, user_id={user_id}")

            # For hard delete, use the record method
            if hard_delete:
                return self.record(entity_type, record_id, user_id)

            # If user_id is provided, verify the record belongs to this user
            if user_id:
                print(f"DEBUG: Verifying record belongs to user {user_id}")
                try:
                    # Get the item first to check ownership
                    response = self.table.get_item(
                        Key={
                            'PK': f"{entity_type.upper()}",
                            'SK': str(record_id)
                        }
                    )

                    if 'Item' not in response:
                        logger.error(f"Record {entity_type}/{record_id} not found")
                        print(f"DEBUG: Record {entity_type}/{record_id} not found")
                        return False

                    item = response['Item']
                    if 'user_id' in item and item['user_id'] != user_id:
                        logger.error(f"Record {entity_type}/{record_id} belongs to a different user")
                        print(f"DEBUG: Record {entity_type}/{record_id} belongs to a different user")
                        return False

                    print(f"DEBUG: Record ownership verified for user {user_id}")
                except Exception as e:
                    logger.error(f"Error verifying record ownership: {str(e)}")
                    print(f"DEBUG: Error verifying record ownership: {str(e)}")
                    return False

            # For soft delete, update the state attribute
            print(f"DEBUG: Soft deleting record {entity_type}/{record_id}")
            update_expression = "SET #state = :state"
            expression_attribute_names = {"#state": "state"}
            expression_attribute_values = {":state": 0}

            # If user_id is provided, also update the user_id field for audit purposes
            if user_id:
                update_expression += ", #last_modified_by = :user"
                expression_attribute_names["#last_modified_by"] = "last_modified_by"
                expression_attribute_values[":user"] = user_id
                print(f"DEBUG: Adding last_modified_by={user_id} to update")

            response = self.table.update_item(
                Key={
                    'PK': f"{entity_type.upper()}",
                    'SK': str(record_id)
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="UPDATED_NEW"
            )

            logger.info(f"Soft deleted {entity_type} record with ID {record_id}")
            print(f"DEBUG: Successfully soft deleted {entity_type} record with ID {record_id}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting entry {entity_type} record {record_id}: {str(e)}")
            print(f"DEBUG: Error deleting entry {entity_type} record {record_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in delete_entry: {str(e)}")
            print(f"DEBUG: Unexpected error in delete_entry: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            return False